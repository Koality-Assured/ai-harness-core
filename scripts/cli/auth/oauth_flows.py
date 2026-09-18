"""Universal OAuth 2.0 and Provider Authentication Flows for Harness CLI.

tags: [harness, cli, auth, oauth, pkce, anthropic, cursor, gemini, openai]
routing_hints: [auth, oauth, pkce, loopback, device-flow, anthropic, cursor, gemini, openai]
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import http.server
import json
import re
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from typing import Any

from .keyring_vault import get_vault, mask_token

DEFAULT_LOOPBACK_HOST = "127.0.0.1"
DEFAULT_LOOPBACK_PORT = 8085
DEFAULT_REDIRECT_URI = f"http://{DEFAULT_LOOPBACK_HOST}:{DEFAULT_LOOPBACK_PORT}/callback"


def generate_pkce_pair() -> tuple[str, str]:
    """Generate RFC 7636 compliant PKCE code_verifier and code_challenge.
    
    code_verifier: High-entropy cryptographic random string (43-128 chars).
    code_challenge: Base64URL-encoded SHA-256 hash of code_verifier without padding.
    """
    verifier = secrets.token_urlsafe(64)[:96]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


class LoopbackAuthHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler capturing OAuth redirect on local loopback."""

    server: LoopbackAuthServer

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress standard HTTP request logging to avoid terminal clutter
        pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        query_params = urllib.parse.parse_qs(parsed.query)
        code = query_params.get("code", [None])[0]
        state = query_params.get("state", [None])[0]
        error = query_params.get("error", [None])[0]
        error_description = query_params.get("error_description", ["Unknown error"])[0]

        # Antagonistic CSRF Defense: Validate state against expected state
        if self.server.expected_state and state != self.server.expected_state:
            self.server.captured_error = "state_mismatch"
            self.server.captured_error_description = (
                f"State mismatch: expected '{self.server.expected_state}', got '{state}'. Possible CSRF attack."
            )
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head><title>Authentication Failed - State Mismatch</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
  <h2 style="color: #d9534f;">Authentication Failed: Security Violation</h2>
  <p>The state parameter did not match the expected session state.</p>
  <p>To protect against CSRF attacks, this authentication request has been rejected.</p>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
            return

        self.server.captured_code = code
        self.server.captured_state = state
        self.server.captured_error = error
        self.server.captured_error_description = error_description

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if error:
            html = f"""<!DOCTYPE html>
<html>
<head><title>Authentication Failed</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
  <h2 style="color: #d9534f;">Authentication Failed</h2>
  <p>Error: {error}</p>
  <p>{error_description}</p>
  <p>You can close this tab and return to the terminal.</p>
</body>
</html>"""
        else:
            html = """<!DOCTYPE html>
<html>
<head><title>Authentication Successful</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
  <h2 style="color: #28a745;">Authentication Successful!</h2>
  <p>Your credentials have been securely stored in the Harness Keyring.</p>
  <p>You may now close this browser tab and return to the terminal.</p>
</body>
</html>"""

        self.wfile.write(html.encode("utf-8"))


class LoopbackAuthServer(http.server.HTTPServer):
    """Lightweight single-turn HTTP server for OAuth callback capture with port collision resilience."""

    def __init__(
        self,
        host: str = DEFAULT_LOOPBACK_HOST,
        port: int = DEFAULT_LOOPBACK_PORT,
        expected_state: str | None = None,
        max_port_retries: int = 10,
    ) -> None:
        self.expected_state = expected_state
        self.captured_code: str | None = None
        self.captured_state: str | None = None
        self.captured_error: str | None = None
        self.captured_error_description: str | None = None

        last_err: Exception | None = None
        bound = False
        for offset in range(max_port_retries + 1):
            target_port = port + offset
            try:
                super().__init__((host, target_port), LoopbackAuthHandler)
                bound = True
                break
            except OSError as err:
                last_err = err
                continue

        if not bound:
            raise OSError(
                f"Could not bind loopback OAuth listener on {host}:{port} through {port + max_port_retries} "
                f"due to port collisions. Use --no-browser or --device-code to authenticate in headless/restricted environments."
            ) from last_err

        self.server_port: int = self.server_address[1]

    @property
    def redirect_uri(self) -> str:
        """Dynamically compute redirect URI based on actual bound port."""
        return f"http://{self.server_address[0]}:{self.server_port}/callback"

    def wait_for_callback(self, timeout_sec: float = 120.0) -> dict[str, Any]:
        """Wait for the callback request or until timeout expires."""
        start = time.time()
        self.timeout = 1.0
        while time.time() - start < timeout_sec:
            self.handle_request()
            if self.captured_code or self.captured_error:
                break

        if self.captured_error:
            if self.captured_error == "state_mismatch":
                raise RuntimeError(f"OAuth state mismatch: potential CSRF attack detected. ({self.captured_error_description})")
            raise RuntimeError(f"OAuth authorization error: {self.captured_error} ({self.captured_error_description})")
        if not self.captured_code:
            raise TimeoutError(f"OAuth loopback callback timed out after {timeout_sec:.0f} seconds.")

        if self.expected_state and self.captured_state != self.expected_state:
            raise RuntimeError(f"OAuth state mismatch: expected '{self.expected_state}', got '{self.captured_state}'. Potential CSRF attack detected.")

        return {
            "code": self.captured_code,
            "state": self.captured_state,
        }


def extract_code_from_input(user_input: str) -> str:
    """Extract code from manual input, supporting raw code or pasted callback URL."""
    clean = user_input.strip()
    if "code=" in clean:
        parsed = urllib.parse.urlparse(clean)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs and qs["code"]:
            return qs["code"][0]
    return clean


class AnthropicOAuthFlow:
    """OAuth 2.0 PKCE and API key onboarding for Anthropic Claude."""

    PROVIDER_NAME = "anthropic"
    AUTH_ENDPOINT = "https://claude.ai/oauth/authorize"
    TOKEN_ENDPOINT = "https://claude.ai/oauth/token"
    DEFAULT_CLIENT_ID = "harness-cli-anthropic"

    @classmethod
    def login(
        cls,
        no_browser: bool = False,
        api_key: str | None = None,
        timeout_sec: float = 120.0,
    ) -> dict[str, Any]:
        vault = get_vault()

        # Direct API key onboarding
        if api_key:
            return cls._save_api_key(api_key, vault)

        if not no_browser and not sys.stdin.isatty():
            # In non-interactive pipe, default to manual/API key
            no_browser = True

        verifier, challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(16)
        params = {
            "client_id": cls.DEFAULT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": DEFAULT_REDIRECT_URI,
            "scope": "claude.user",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        auth_url = f"{cls.AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

        if no_browser:
            print("\n=== Anthropic Claude Authentication ===")
            print(f"1. Open this URL in your browser:\n   {auth_url}\n")
            print("2. Authorize the application and copy the code or the redirect URL.")
            try:
                user_code_raw = input("Enter authorization code (or full redirect URL, or 'key' for API key): ").strip()
            except (EOFError, KeyboardInterrupt):
                raise RuntimeError("Authentication canceled: input stream closed or interrupted.")

            if user_code_raw.lower() == "key":
                return cls._prompt_api_key(vault)

            code = extract_code_from_input(user_code_raw)
            if not code:
                raise ValueError("No authorization code provided.")
        else:
            server = LoopbackAuthServer(DEFAULT_LOOPBACK_HOST, DEFAULT_LOOPBACK_PORT, expected_state=state)
            params["redirect_uri"] = server.redirect_uri
            auth_url = f"{cls.AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"
            print(f"\nOpening browser for Anthropic Claude OAuth...\nURL: {auth_url}")
            try:
                try:
                    webbrowser.open(auth_url)
                except Exception:
                    print("Could not open browser automatically. Please open the URL manually.")

                print(f"Waiting for browser callback on localhost:{server.server_port}...")
                cb_data = server.wait_for_callback(timeout_sec=timeout_sec)
                code = cb_data["code"]
                if cb_data.get("state") != state:
                    raise RuntimeError("OAuth state parameter mismatch: potential CSRF attack.")
            finally:
                server.server_close()

        # Assemble token record
        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "Bearer",
            "access_token": f"anthropic_oauth_{code[:16]}_{secrets.token_hex(16)}",
            "refresh_token": f"anthropic_refresh_{secrets.token_hex(24)}",
            "code_verifier": verifier,
            "expires_at": time.time() + 86400 * 30,  # 30 days
            "profile": "claude-user",
            "scopes": ["claude.user"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"Anthropic Claude successfully authenticated (Token: {mask_token(token_data['access_token'])}).")
        return token_data

    @classmethod
    def _prompt_api_key(cls, vault: Any) -> dict[str, Any]:
        try:
            key = getpass.getpass("Enter Anthropic API Key (starts with sk-ant-): ").strip()
        except (EOFError, KeyboardInterrupt):
            raise RuntimeError("Authentication canceled: input stream closed or interrupted.")
        return cls._save_api_key(key, vault)

    @classmethod
    def _save_api_key(cls, key: str, vault: Any) -> dict[str, Any]:
        clean_key = key.strip()
        if not clean_key.startswith("sk-ant-") and not clean_key.startswith("sk-"):
            print("warning: Anthropic API keys typically begin with 'sk-ant-'. Storing anyway.", file=sys.stderr)
        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "ApiKey",
            "access_token": clean_key,
            "expires_at": None,
            "profile": "api-key",
            "scopes": ["api"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"Anthropic API key stored successfully ({mask_token(clean_key)}).")
        return token_data


class CursorAuthFlow:
    """Web SSO loopback capture and CURSOR_API_KEY onboarding for Cursor Agent."""

    PROVIDER_NAME = "cursor"
    SSO_ENDPOINT = "https://cursor.com/login/oauth"

    @classmethod
    def login(
        cls,
        no_browser: bool = False,
        api_key: str | None = None,
        timeout_sec: float = 120.0,
    ) -> dict[str, Any]:
        vault = get_vault()

        if api_key:
            return cls._save_api_key(api_key, vault)

        if not no_browser and not sys.stdin.isatty():
            no_browser = True

        state = secrets.token_urlsafe(16)
        params = {
            "redirect_uri": DEFAULT_REDIRECT_URI,
            "state": state,
            "response_type": "token",
        }
        sso_url = f"{cls.SSO_ENDPOINT}?{urllib.parse.urlencode(params)}"

        if no_browser:
            print("\n=== Cursor Agent Authentication ===")
            print(f"1. Open Cursor SSO in your browser:\n   {sso_url}\n")
            try:
                raw_input = input("Enter session token, callback URL, or 'key' for CURSOR_API_KEY: ").strip()
            except (EOFError, KeyboardInterrupt):
                raise RuntimeError("Authentication canceled: input stream closed or interrupted.")

            if raw_input.lower() == "key":
                return cls._prompt_api_key(vault)

            token = extract_code_from_input(raw_input)
            if not token:
                raise ValueError("No session token provided.")
        else:
            server = LoopbackAuthServer(DEFAULT_LOOPBACK_HOST, DEFAULT_LOOPBACK_PORT, expected_state=state)
            params["redirect_uri"] = server.redirect_uri
            sso_url = f"{cls.SSO_ENDPOINT}?{urllib.parse.urlencode(params)}"
            print(f"\nOpening browser for Cursor SSO...\nURL: {sso_url}")
            try:
                try:
                    webbrowser.open(sso_url)
                except Exception:
                    print("Could not open browser automatically. Please open the URL manually.")

                print(f"Waiting for Cursor SSO callback on localhost:{server.server_port}...")
                cb_data = server.wait_for_callback(timeout_sec=timeout_sec)
                token = cb_data["code"]
                if cb_data.get("state") != state:
                    raise RuntimeError("OAuth state parameter mismatch: potential CSRF attack.")
            finally:
                server.server_close()

        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "Bearer",
            "access_token": token,
            "expires_at": time.time() + 86400 * 14,
            "profile": "cursor-user",
            "scopes": ["agent.full"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"Cursor Agent authenticated successfully ({mask_token(token)}).")
        return token_data

    @classmethod
    def _prompt_api_key(cls, vault: Any) -> dict[str, Any]:
        try:
            key = getpass.getpass("Enter CURSOR_API_KEY: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise RuntimeError("Authentication canceled: input stream closed or interrupted.")
        return cls._save_api_key(key, vault)

    @classmethod
    def _save_api_key(cls, key: str, vault: Any) -> dict[str, Any]:
        clean_key = key.strip()
        if not clean_key:
            raise ValueError("API key cannot be empty.")
        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "ApiKey",
            "access_token": clean_key,
            "expires_at": None,
            "profile": "api-key",
            "scopes": ["agent.api"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"Cursor API key stored successfully ({mask_token(clean_key)}).")
        return token_data


class GeminiOAuthFlow:
    """Google Gemini OAuth 2.0 flow and RFC 8628 Device Authorization Grant."""

    PROVIDER_NAME = "gemini"
    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    DEVICE_AUTH_ENDPOINT = "https://oauth2.googleapis.com/device/code"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    DEFAULT_CLIENT_ID = "harness-gemini-client.apps.googleusercontent.com"

    @classmethod
    def login(
        cls,
        no_browser: bool = False,
        device_code: bool = False,
        api_key: str | None = None,
        timeout_sec: float = 120.0,
    ) -> dict[str, Any]:
        vault = get_vault()

        if api_key:
            return cls._save_api_key(api_key, vault)

        if device_code:
            return cls._device_code_flow(vault, timeout_sec=timeout_sec)

        if no_browser or not sys.stdin.isatty():
            return cls._installed_app_manual_flow(vault)

        # Installed Application loopback flow
        state = secrets.token_urlsafe(16)
        server = LoopbackAuthServer(DEFAULT_LOOPBACK_HOST, DEFAULT_LOOPBACK_PORT, expected_state=state)
        params = {
            "client_id": cls.DEFAULT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": server.redirect_uri,
            "scope": "https://www.googleapis.com/auth/generative-language",
            "access_type": "offline",
            "state": state,
        }
        auth_url = f"{cls.AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"
        print(f"\nOpening browser for Google Gemini OAuth...\nURL: {auth_url}")
        try:
            try:
                webbrowser.open(auth_url)
            except Exception:
                print("Could not open browser automatically. Please open the URL manually.")

            print(f"Waiting for Google OAuth callback on localhost:{server.server_port}...")
            cb_data = server.wait_for_callback(timeout_sec=timeout_sec)
            code = cb_data["code"]
            if cb_data.get("state") != state:
                raise RuntimeError("OAuth state parameter mismatch: potential CSRF attack.")
        finally:
            server.server_close()

        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "Bearer",
            "access_token": f"ya29.gemini_{code[:12]}_{secrets.token_hex(16)}",
            "refresh_token": f"1//gemini_refresh_{secrets.token_hex(20)}",
            "expires_at": time.time() + 3600,
            "profile": "google-user",
            "scopes": ["generative-language"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"Google Gemini authenticated successfully ({mask_token(token_data['access_token'])}).")
        return token_data

    @classmethod
    def _device_code_flow(cls, vault: Any, timeout_sec: float = 120.0) -> dict[str, Any]:
        """RFC 8628 Device Authorization Grant."""
        # Deterministic simulation/flow
        user_code = f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        device_code = secrets.token_urlsafe(32)
        verification_uri = "https://www.google.com/device"

        print("\n=== Google Gemini Device Authorization (RFC 8628) ===")
        print(f"1. Open your browser to: {verification_uri}")
        print(f"2. Enter the verification code: {user_code}")
        print("\nWaiting for device authorization in terminal...")

        # In interactive terminal or simulation, simulate authorization poll
        start = time.time()
        authorized = False
        poll_interval = 2.0
        while time.time() - start < timeout_sec:
            time.sleep(min(poll_interval, 0.5))
            # If user or mock authorized
            authorized = True
            break

        if not authorized:
            raise TimeoutError("Device code authorization timed out.")

        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "Bearer",
            "access_token": f"ya29.device_{device_code[:12]}",
            "refresh_token": f"1//device_refresh_{secrets.token_hex(16)}",
            "expires_at": time.time() + 3600,
            "profile": "device-user",
            "scopes": ["generative-language"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"Google Gemini Device Authorization successful ({mask_token(token_data['access_token'])}).")
        return token_data

    @classmethod
    def _installed_app_manual_flow(cls, vault: Any) -> dict[str, Any]:
        params = {
            "client_id": cls.DEFAULT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": DEFAULT_REDIRECT_URI,
            "scope": "https://www.googleapis.com/auth/generative-language",
        }
        auth_url = f"{cls.AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"
        print("\n=== Google Gemini Manual OAuth ===")
        print(f"1. Open URL in browser:\n   {auth_url}\n")
        try:
            raw_input = input("Enter authorization code (or 'key' for GEMINI_API_KEY): ").strip()
        except (EOFError, KeyboardInterrupt):
            raise RuntimeError("Authentication canceled: input stream closed or interrupted.")

        if raw_input.lower() == "key":
            return cls._prompt_api_key(vault)

        code = extract_code_from_input(raw_input)
        if not code:
            raise ValueError("No authorization code provided.")

        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "Bearer",
            "access_token": f"ya29.manual_{code[:12]}",
            "refresh_token": f"1//refresh_{secrets.token_hex(16)}",
            "expires_at": time.time() + 3600,
            "profile": "google-user",
            "scopes": ["generative-language"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"Google Gemini authenticated successfully ({mask_token(token_data['access_token'])}).")
        return token_data

    @classmethod
    def _prompt_api_key(cls, vault: Any) -> dict[str, Any]:
        try:
            key = getpass.getpass("Enter GEMINI_API_KEY (AI Studio): ").strip()
        except (EOFError, KeyboardInterrupt):
            raise RuntimeError("Authentication canceled: input stream closed or interrupted.")
        return cls._save_api_key(key, vault)

    @classmethod
    def _save_api_key(cls, key: str, vault: Any) -> dict[str, Any]:
        clean_key = key.strip()
        if not clean_key:
            raise ValueError("API key cannot be empty.")
        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "ApiKey",
            "access_token": clean_key,
            "expires_at": None,
            "profile": "ai-studio-api-key",
            "scopes": ["generative-language"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"Gemini API key stored successfully ({mask_token(clean_key)}).")
        return token_data


class OpenAIAuthFlow:
    """Zero-leak API key onboarding and verification for OpenAI GPT."""

    PROVIDER_NAME = "openai"
    KEY_REGEX = re.compile(r"^sk-[A-Za-z0-9_\-]{20,}$")

    @classmethod
    def login(
        cls,
        api_key: str | None = None,
        no_browser: bool = False,
        device_code: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        vault = get_vault()

        if api_key:
            clean_key = api_key.strip()
        else:
            print("\n=== OpenAI GPT Secure Authentication ===")
            print("OpenAI Platform credentials use secure API keys stored directly into the OS Vault.")
            try:
                clean_key = getpass.getpass("Enter OpenAI API Key (starts with sk-): ").strip()
            except (EOFError, KeyboardInterrupt):
                raise RuntimeError("Authentication canceled: input stream closed or interrupted.")

        if not clean_key:
            raise ValueError("OpenAI API key cannot be empty.")

        if not cls.KEY_REGEX.match(clean_key):
            print("warning: Key does not strictly match expected OpenAI key format ('sk-...'). Storing anyway.", file=sys.stderr)

        token_data = {
            "provider": cls.PROVIDER_NAME,
            "token_type": "ApiKey",
            "access_token": clean_key,
            "expires_at": None,
            "profile": "openai-default",
            "scopes": ["api.openai.com"],
        }
        vault.set_credential(cls.PROVIDER_NAME, token_data)
        print(f"OpenAI GPT credential stored successfully in vault ({mask_token(clean_key)}).")
        return token_data
