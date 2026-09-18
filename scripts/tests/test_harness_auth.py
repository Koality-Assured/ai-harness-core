"""Unit tests for Harness CLI Universal Auth Subsystem and Keyring Manager.

tags: [tests, harness, cli, auth, keyring, oauth, security]
routing_hints: [tests, auth, keyring, vault, oauth, pkce, sanitization]

Run: python -m unittest scripts.tests.test_harness_auth -v
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_SCRIPTS = Path(__file__).resolve().parents[1]
_CLI = _SCRIPTS / "cli"
_LIB = _SCRIPTS / "_lib"
for _p in (str(_CLI), str(_SCRIPTS), str(_LIB)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli.auth.keyring_vault import (
    EncryptedFileVault,
    KeyringVault,
    UniversalVault,
    is_token_expired,
    mask_token,
)
from cli.auth.oauth_flows import (
    AnthropicOAuthFlow,
    CursorAuthFlow,
    GeminiOAuthFlow,
    LoopbackAuthServer,
    OpenAIAuthFlow,
    extract_code_from_input,
    generate_pkce_pair,
)
from harness import main


class TestPKCE(unittest.TestCase):
    """Test RFC 7636 PKCE code_verifier and code_challenge generation."""

    def test_pkce_generation(self) -> None:
        verifier, challenge = generate_pkce_pair()
        self.assertGreaterEqual(len(verifier), 43)
        self.assertLessEqual(len(verifier), 128)
        self.assertNotIn("=", challenge)  # Unpadded base64url

        # Verify challenge computation matches RFC 7636: BASE64URL(SHA256(ASCII(verifier)))
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        self.assertEqual(challenge, expected_challenge)

    def test_pkce_rfc7636_test_vector(self) -> None:
        # RFC 7636 Appendix B test vector
        test_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        digest = hashlib.sha256(test_verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        expected = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        self.assertEqual(challenge, expected)

    def test_extract_code_from_input(self) -> None:
        self.assertEqual(extract_code_from_input("my-auth-code-123"), "my-auth-code-123")
        url_input = "http://127.0.0.1:8085/callback?code=captured_code_xyz&state=abc"
        self.assertEqual(extract_code_from_input(url_input), "captured_code_xyz")


class TestCredentialSanitization(unittest.TestCase):
    """Test zero plaintext token leakage in logs and terminal representations."""

    def test_mask_token_long(self) -> None:
        token = "sk-ant-api03-1234567890abcdefghijklmnopqr"
        masked = mask_token(token)
        self.assertTrue(masked.startswith("sk-ant"))
        self.assertTrue(masked.endswith("nopqr"[-4:]))
        self.assertNotIn("1234567890abcdef", masked)
        self.assertIn("...", masked)

    def test_mask_token_short(self) -> None:
        self.assertEqual(mask_token("short"), "***")
        self.assertEqual(mask_token(""), "")
        self.assertEqual(mask_token(None), "")

    def test_is_token_expired(self) -> None:
        now = time.time()
        # Non-expiring (API Key)
        self.assertFalse(is_token_expired({"access_token": "abc", "expires_at": None}))
        self.assertFalse(is_token_expired({"access_token": "abc"}))

        # Expired in past
        self.assertTrue(is_token_expired({"access_token": "abc", "expires_at": now - 100}))

        # Valid in future
        self.assertFalse(is_token_expired({"access_token": "abc", "expires_at": now + 3600}))

        # Within buffer (expires in 30s, buffer is 60s)
        self.assertTrue(is_token_expired({"access_token": "abc", "expires_at": now + 30}, buffer_seconds=60))

        # ISO string parsing
        future_iso = "2099-01-01T00:00:00Z"
        self.assertFalse(is_token_expired({"access_token": "abc", "expires_at": future_iso}))
        past_iso = "2020-01-01T00:00:00Z"
        self.assertTrue(is_token_expired({"access_token": "abc", "expires_at": past_iso}))


class TestEncryptedFileVault(unittest.TestCase):
    """Test AES-256-GCM and PBKDF2 encrypted file vault."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_file = Path(self.temp_dir.name) / "credentials.enc"
        self.passphrase = "test-secret-passphrase-123"
        self.vault = EncryptedFileVault(vault_path=self.vault_file, passphrase=self.passphrase)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_crud_cycle(self) -> None:
        # Initially empty
        self.assertEqual(self.vault.list_providers(), [])
        self.assertIsNone(self.vault.get_credential("anthropic"))

        # Set credential
        token_data = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "profile": "user@example.com",
        }
        self.vault.set_credential("anthropic", token_data)

        # File created
        self.assertTrue(self.vault_file.exists())

        # Retrieve credential
        retrieved = self.vault.get_credential("anthropic")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["access_token"], "test-access-token")
        self.assertIn("updated_at", retrieved)

        # List providers
        self.assertEqual(self.vault.list_providers(), ["anthropic"])

        # Delete credential
        deleted = self.vault.delete_credential("anthropic")
        self.assertTrue(deleted)
        self.assertEqual(self.vault.list_providers(), [])
        self.assertIsNone(self.vault.get_credential("anthropic"))

        # Nonexistent delete returns False
        self.assertFalse(self.vault.delete_credential("anthropic"))

    def test_wrong_passphrase_fails(self) -> None:
        self.vault.set_credential("gemini", {"access_token": "ya29.test"})

        # Try to open with wrong passphrase
        wrong_vault = EncryptedFileVault(vault_path=self.vault_file, passphrase="wrong-passphrase")
        with self.assertRaises(ValueError):
            wrong_vault.get_credential("gemini")

    def test_corrupted_file_fails(self) -> None:
        self.vault_file.write_bytes(b"corrupt-non-magic-data")
        with self.assertRaises(ValueError):
            self.vault.get_credential("openai")

    def test_tampered_ciphertext_fails(self) -> None:
        self.vault.set_credential("anthropic", {"access_token": "valid-secret-token"})
        raw = bytearray(self.vault_file.read_bytes())
        # Corrupt a byte in ciphertext (after magic + salt + nonce = 32 bytes)
        raw[35] ^= 0xFF
        self.vault_file.write_bytes(bytes(raw))

        with self.assertRaises(ValueError) as ctx:
            self.vault.get_credential("anthropic")
        self.assertIn("Authentication tag verification failed", str(ctx.exception))

    def test_tampered_header_fails(self) -> None:
        self.vault.set_credential("cursor", {"access_token": "cur-secret-999"})
        raw = self.vault_file.read_bytes()
        tampered = b"BAD1" + raw[4:]
        self.vault_file.write_bytes(tampered)

        with self.assertRaises(ValueError) as ctx:
            self.vault.get_credential("cursor")
        self.assertIn("Invalid or corrupted vault file header", str(ctx.exception))

    def test_corrupted_vault_recovery(self) -> None:
        self.vault_file.write_bytes(b"garbage-data-simulating-corruption")
        # Writing a new credential to a corrupted vault must safely back up and re-initialize
        self.vault.set_credential("openai", {"access_token": "sk-recovered-key"})
        cred = self.vault.get_credential("openai")
        self.assertIsNotNone(cred)
        self.assertEqual(cred["access_token"], "sk-recovered-key")
        # Verify a .corrupted. backup was created
        backups = list(self.vault_file.parent.glob("credentials.enc.corrupted.*"))
        self.assertGreaterEqual(len(backups), 1)

    def test_machine_bound_key_derivation_profiles(self) -> None:
        from cli.auth.keyring_vault import EncryptedFileVault

        # Profile 1: Normal environment
        v1 = EncryptedFileVault(vault_path=self.vault_file)
        pass1 = v1._get_passphrase()
        self.assertTrue(pass1.startswith("harness-vault:"))

        # Profile 2: Container environment with stripped USER and USERNAME and no getlogin
        with patch("os.getlogin", side_effect=OSError("No login session")):
            with patch.dict(os.environ, {"USER": "", "USERNAME": ""}, clear=False):
                v2 = EncryptedFileVault(vault_path=self.vault_file)
                pass2 = v2._get_passphrase()
                self.assertTrue(pass2.startswith("harness-vault:"))

    def test_file_permissions_enforcement(self) -> None:
        from cli.auth.keyring_vault import _enforce_private_permissions

        self.vault.set_credential("gemini", {"access_token": "ya29.perm_test"})
        self.assertTrue(self.vault_file.exists())
        # Calling permission enforcement directly should not raise
        _enforce_private_permissions(self.vault_file)

    def test_vault_concurrency_multi_provider(self) -> None:
        import concurrent.futures

        providers = [f"provider_{i}" for i in range(10)]

        def worker(p: str) -> None:
            self.vault.set_credential(p, {"access_token": f"token_for_{p}"})
            retrieved = self.vault.get_credential(p)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["access_token"], f"token_for_{p}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, p) for p in providers]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        stored = self.vault.list_providers()
        for p in providers:
            self.assertIn(p, stored)


class TestKeyringVault(unittest.TestCase):
    """Test OS-native Keyring vault wrapper and fallback."""

    def test_keyring_mock_crud(self) -> None:
        fake_storage: dict[str, str] = {}

        mock_keyring = MagicMock()
        mock_backend = MagicMock()
        mock_backend.__class__.__name__ = "WinVaultKeyring"
        mock_keyring.get_keyring.return_value = mock_backend

        def fake_get_password(service, username):
            return fake_storage.get(f"{service}:{username}")

        def fake_set_password(service, username, password):
            fake_storage[f"{service}:{username}"] = password

        def fake_delete_password(service, username):
            key = f"{service}:{username}"
            if key in fake_storage:
                del fake_storage[key]
            else:
                raise Exception("Not found")

        mock_keyring.get_password.side_effect = fake_get_password
        mock_keyring.set_password.side_effect = fake_set_password
        mock_keyring.delete_password.side_effect = fake_delete_password

        kv = KeyringVault(service_name="test-harness")
        kv._keyring = mock_keyring
        self.assertTrue(kv.is_available)

        kv.set_credential("openai", {"access_token": "sk-1234567890"})
        cred = kv.get_credential("openai")
        self.assertIsNotNone(cred)
        self.assertEqual(cred["access_token"], "sk-1234567890")
        self.assertIn("openai", kv.list_providers())

        self.assertTrue(kv.delete_credential("openai"))
        self.assertIsNone(kv.get_credential("openai"))

    def test_universal_vault_fallback_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vf = Path(td) / "credentials.enc"
            # Force file vault mode
            uv = UniversalVault(vault_path=vf, passphrase="fallback-passphrase", force_file_vault=True)
            self.assertEqual(uv.active_backend_name, "encrypted_file")

            uv.set_credential("cursor", {"access_token": "cursor-token-999"})
            cred = uv.get_credential("cursor")
            self.assertIsNotNone(cred)
            self.assertEqual(cred["access_token"], "cursor-token-999")
            self.assertEqual(uv.list_providers(), ["cursor"])


class TestOAuthFlows(unittest.TestCase):
    """Test OAuth flows for Claude, Cursor, Gemini, and OpenAI."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_file = Path(self.temp_dir.name) / "credentials.enc"
        self.vault = UniversalVault(vault_path=self.vault_file, force_file_vault=True)
        self.patch_vault = patch("cli.auth.keyring_vault.get_vault", return_value=self.vault)
        self.patch_oauth_vault = patch("cli.auth.oauth_flows.get_vault", return_value=self.vault)
        self.patch_vault.start()
        self.patch_oauth_vault.start()

    def tearDown(self) -> None:
        self.patch_oauth_vault.stop()
        self.patch_vault.stop()
        self.temp_dir.cleanup()

    def test_anthropic_api_key_onboarding(self) -> None:
        res = AnthropicOAuthFlow.login(api_key="sk-ant-test-key-1234567890abcdef")
        self.assertEqual(res["provider"], "anthropic")
        self.assertEqual(res["token_type"], "ApiKey")
        self.assertEqual(res["access_token"], "sk-ant-test-key-1234567890abcdef")

        saved = self.vault.get_credential("anthropic")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["access_token"], "sk-ant-test-key-1234567890abcdef")

    def test_cursor_api_key_onboarding(self) -> None:
        res = CursorAuthFlow.login(api_key="cur_live_token1234567890abcdef")
        self.assertEqual(res["provider"], "cursor")
        self.assertEqual(res["token_type"], "ApiKey")
        saved = self.vault.get_credential("cursor")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["access_token"], "cur_live_token1234567890abcdef")

    def test_gemini_device_code_flow(self) -> None:
        res = GeminiOAuthFlow.login(device_code=True, timeout_sec=2.0)
        self.assertEqual(res["provider"], "gemini")
        self.assertEqual(res["token_type"], "Bearer")
        self.assertTrue(res["access_token"].startswith("ya29.device_"))
        saved = self.vault.get_credential("gemini")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["access_token"], res["access_token"])

    def test_gemini_api_key_onboarding(self) -> None:
        res = GeminiOAuthFlow.login(api_key="AIzaSyTestGeminiKey1234567890")
        self.assertEqual(res["provider"], "gemini")
        self.assertEqual(res["token_type"], "ApiKey")
        saved = self.vault.get_credential("gemini")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["access_token"], "AIzaSyTestGeminiKey1234567890")

    def test_openai_api_key_onboarding(self) -> None:
        res = OpenAIAuthFlow.login(api_key="sk-proj-testkey1234567890abcdef123456")
        self.assertEqual(res["provider"], "openai")
        self.assertEqual(res["token_type"], "ApiKey")
        saved = self.vault.get_credential("openai")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["access_token"], "sk-proj-testkey1234567890abcdef123456")


class TestAuthCLICommands(unittest.TestCase):
    """Test CLI subcommand integration: harness auth login/status/logout."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_file = Path(self.temp_dir.name) / "credentials.enc"
        self.vault = UniversalVault(vault_path=self.vault_file, force_file_vault=True)
        self.patch_vault1 = patch("cli.auth.get_vault", return_value=self.vault)
        self.patch_vault2 = patch("cli.auth.keyring_vault.get_vault", return_value=self.vault)
        self.patch_vault3 = patch("cli.auth.oauth_flows.get_vault", return_value=self.vault)
        self.patch_vault1.start()
        self.patch_vault2.start()
        self.patch_vault3.start()

    def tearDown(self) -> None:
        self.patch_vault3.stop()
        self.patch_vault2.stop()
        self.patch_vault1.stop()
        self.temp_dir.cleanup()

    def test_auth_status_initial_empty(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["auth", "status"])
        self.assertEqual(ret, 0)
        out = capture.getvalue()
        self.assertIn("Harness Credential Vault Status", out)
        self.assertIn("NOT AUTHENTICATED", out)

    def test_auth_status_json(self) -> None:
        # Pre-seed one credential
        self.vault.set_credential("anthropic", {
            "access_token": "sk-ant-test-token-123456789",
            "token_type": "ApiKey",
            "profile": "test-profile",
            "expires_at": None,
        })

        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["auth", "status", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(capture.getvalue())
        self.assertIn("active_vault_backend", data)
        self.assertIn("providers", data)

        anthropic_stat = next(p for p in data["providers"] if p["provider"] == "anthropic")
        self.assertTrue(anthropic_stat["authenticated"])
        self.assertEqual(anthropic_stat["status"], "VALID")
        # Ensure plaintext secret is NEVER exposed in status JSON
        self.assertNotIn("sk-ant-test-token-123456789", capture.getvalue())
        self.assertTrue(anthropic_stat["token_masked"].startswith("sk-ant"))

    def test_auth_login_via_cli(self) -> None:
        ret = main(["auth", "login", "openai", "--api-key", "sk-proj-testkey1234567890abcdef123456"])
        self.assertEqual(ret, 0)
        saved = self.vault.get_credential("openai")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["access_token"], "sk-proj-testkey1234567890abcdef123456")

    def test_auth_logout_single(self) -> None:
        self.vault.set_credential("cursor", {"access_token": "cur_12345"})
        self.assertIsNotNone(self.vault.get_credential("cursor"))

        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["auth", "logout", "cursor"])
        self.assertEqual(ret, 0)
        self.assertIn("Logged out from 'cursor'", capture.getvalue())
        self.assertIsNone(self.vault.get_credential("cursor"))

    def test_auth_logout_all(self) -> None:
        self.vault.set_credential("gemini", {"access_token": "ya29.123"})
        self.vault.set_credential("openai", {"access_token": "sk-123"})

        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["auth", "logout", "--all"])
        self.assertEqual(ret, 0)
        self.assertIn("Successfully purged all credentials", capture.getvalue())
        self.assertEqual(self.vault.list_providers(), [])

    def test_auth_login_invalid_provider(self) -> None:
        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            with self.assertRaises(SystemExit) as ctx:
                main(["auth", "login", "nonexistent_provider_xyz"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("invalid choice", err_capture.getvalue())

    def test_auth_logout_nonexistent(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["auth", "logout", "gemini"])
        self.assertEqual(ret, 0)
        self.assertIn("No stored credentials found for 'gemini'", capture.getvalue())

    def test_auth_login_api_key_warning(self) -> None:
        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            ret = main(["auth", "login", "openai", "--api-key", "sk-proj-testkey1234567890abcdef123456"])
        self.assertEqual(ret, 0)
        self.assertIn("warning: providing secrets via the '--api-key' CLI argument", err_capture.getvalue())


class TestLoopbackAndOAuthSecurity(unittest.TestCase):
    """Test OAuth PKCE loopback server security, state CSRF verification, and port collisions."""

    def test_state_parameter_mismatch_rejection(self) -> None:
        import threading
        import urllib.error
        import urllib.request

        server = LoopbackAuthServer(host="127.0.0.1", port=8085, expected_state="expected-secret-state-999")
        port = server.server_port

        def send_attack():
            time.sleep(0.1)
            attack_url = f"http://127.0.0.1:{port}/callback?code=evil_code&state=ATTACKER_INJECTED_STATE"
            try:
                urllib.request.urlopen(attack_url, timeout=2.0)
            except urllib.error.HTTPError as e:
                # Expect 400 Bad Request
                self.assertEqual(e.code, 400)

        t = threading.Thread(target=send_attack)
        t.daemon = True
        t.start()

        with self.assertRaises(RuntimeError) as ctx:
            server.wait_for_callback(timeout_sec=5.0)
        self.assertIn("OAuth state mismatch", str(ctx.exception))
        server.server_close()

    def test_port_binding_collision_handling(self) -> None:
        import socket

        # Bind a dummy socket on port 8085 or an ephemeral port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        busy_port = sock.getsockname()[1]

        try:
            # LoopbackAuthServer should detect busy_port and bind to busy_port + 1 without error
            server = LoopbackAuthServer(host="127.0.0.1", port=busy_port, max_port_retries=5)
            self.assertNotEqual(server.server_port, busy_port)
            self.assertEqual(server.server_port, busy_port + 1)
            server.server_close()
        finally:
            sock.close()

    def test_piped_stdin_closed_stream(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault_file = Path(td) / "credentials.enc"
            vault = UniversalVault(vault_path=vault_file, force_file_vault=True)
            with patch("cli.auth.oauth_flows.get_vault", return_value=vault):
                # Simulated closed stdin raising EOFError
                with patch("builtins.input", side_effect=EOFError):
                    with self.assertRaises(RuntimeError) as ctx:
                        AnthropicOAuthFlow.login(no_browser=True)
                    self.assertIn("Authentication canceled", str(ctx.exception))

                # Simulated closed stdin in getpass
                with patch("getpass.getpass", side_effect=EOFError):
                    with self.assertRaises(RuntimeError) as ctx:
                        OpenAIAuthFlow.login()
                    self.assertIn("Authentication canceled", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
