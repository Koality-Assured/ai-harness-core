"""Universal Keyring & Encrypted File Vault for Harness CLI.

tags: [harness, cli, auth, keyring, vault, security]
routing_hints: [auth, keyring, vault, credential, security, wincred, keychain, libsecret]
"""

from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import sys
import threading
import time
from pathlib import Path
from typing import Any

# Service name for OS-native keyring storage
HARNESS_KEYRING_SERVICE = os.environ.get("HARNESS_KEYRING_SERVICE", "harness-control-plane")
HARNESS_PROVIDERS_KEY = "__harness_providers__"
MAGIC_HEADER = b"HNC1"  # Harness Encrypted Credentials v1


def mask_token(token: str | None, visible_start: int = 6, visible_end: int = 4) -> str:
    """Mask secret token to prevent plaintext leakage in terminal output or logs."""
    if not token:
        return ""
    token_str = str(token).strip()
    if len(token_str) <= 8:
        return "***"
    if len(token_str) <= (visible_start + visible_end + 3):
        return f"{token_str[:2]}...{token_str[-2:]}"
    return f"{token_str[:visible_start]}...{token_str[-visible_end:]}"


def _enforce_private_permissions(path: Path) -> None:
    """Enforce strict user-only read/write permissions on secret files (0600 on POSIX, restricted ACLs on Windows)."""
    if not path.exists():
        return
    if os.name == "nt":
        user = os.environ.get("USERNAME")
        if user:
            try:
                import subprocess

                subprocess.run(
                    ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:(R,W)"],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
    else:
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass


def _enforce_private_dir_permissions(path: Path) -> None:
    """Enforce strict user-only permissions on directory (0700 on POSIX)."""
    if not path.exists():
        return
    if os.name != "nt":
        try:
            os.chmod(path, 0o700)
        except Exception:
            pass


def is_token_expired(token_data: dict[str, Any], buffer_seconds: int = 60) -> bool:
    """Check if token_data has expired or is within buffer_seconds of expiration."""
    exp = token_data.get("expires_at")
    if not exp:
        return False
    try:
        if isinstance(exp, (int, float)):
            exp_ts = float(exp)
        elif isinstance(exp, str):
            # Parse ISO timestamp or string float
            try:
                exp_ts = float(exp)
            except ValueError:
                exp_dt = dt.datetime.fromisoformat(exp.replace("Z", "+00:00"))
                exp_ts = exp_dt.timestamp()
        else:
            return False
        return (time.time() + buffer_seconds) >= exp_ts
    except Exception:
        return False


class EncryptedFileVault:
    """Headless fallback vault using AES-256-GCM and PBKDF2 encryption.
    
    Stores credentials in ~/.harness/credentials.enc (or path from HARNESS_VAULT_PATH).
    Protected by a master passphrase (HARNESS_VAULT_PASSPHRASE) or machine-bound salt.
    """

    def __init__(self, vault_path: Path | str | None = None, passphrase: str | None = None) -> None:
        if vault_path:
            self.path = Path(vault_path).resolve()
        elif os.environ.get("HARNESS_VAULT_PATH"):
            self.path = Path(os.environ["HARNESS_VAULT_PATH"]).resolve()
        else:
            self.path = (Path.home() / ".harness" / "credentials.enc").resolve()

        self._passphrase = passphrase or os.environ.get("HARNESS_VAULT_PASSPHRASE")
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"<EncryptedFileVault path={self.path}>"

    def __str__(self) -> str:
        return self.__repr__()

    def _get_passphrase(self) -> str:
        if self._passphrase:
            return self._passphrase
        # Machine-bound fallback for headless / automated agent runs
        try:
            user = os.getlogin()
        except Exception:
            user = os.environ.get("USERNAME") or os.environ.get("USER")
            if not user:
                try:
                    user = Path.home().name or "agent"
                except Exception:
                    user = "agent"
        try:
            home_str = str(Path.home().resolve())
        except Exception:
            home_str = "/root"
        return f"harness-vault:{user}:{home_str}"

    def _derive_key(self, salt: bytes) -> bytes:
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        except ImportError as exc:
            raise RuntimeError(
                "Optional dependency 'cryptography' is missing for encrypted file vault operations. "
                "Install it via 'pip install cryptography' or configure the OS keyring."
            ) from exc

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return kdf.derive(self._get_passphrase().encode("utf-8"))

    def _load_all(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            raw = self.path.read_bytes()
            if not raw:
                return {}
            min_len = len(MAGIC_HEADER) + 16 + 12 + 16
            if len(raw) < min_len or not raw.startswith(MAGIC_HEADER):
                raise ValueError(
                    f"Invalid or corrupted vault file header at {self.path}. "
                    "File is truncated or missing MAGIC_HEADER."
                )

            salt = raw[4:20]
            nonce = raw[20:32]
            ciphertext = raw[32:]

            try:
                from cryptography.exceptions import InvalidTag
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            except ImportError as exc:
                raise RuntimeError(
                    "Optional dependency 'cryptography' is missing for encrypted file vault operations. "
                    "Install it via 'pip install cryptography' or configure the OS keyring."
                ) from exc

            key = self._derive_key(salt)
            aesgcm = AESGCM(key)
            try:
                plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=MAGIC_HEADER)
            except InvalidTag as it_exc:
                raise ValueError(
                    f"Authentication tag verification failed for vault at {self.path}: "
                    "ciphertext or header has been tampered with, or key/passphrase is incorrect."
                ) from it_exc

            return json.loads(plaintext.decode("utf-8"))
        except (ValueError, RuntimeError):
            raise
        except Exception as exc:
            raise ValueError(f"Failed to decrypt vault at {self.path}: {exc}") from exc

    def _save_all(self, data: dict[str, dict[str, Any]]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _enforce_private_dir_permissions(self.path.parent)

            salt = secrets.token_bytes(16)
            nonce = secrets.token_bytes(12)

            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            except ImportError as exc:
                raise RuntimeError(
                    "Optional dependency 'cryptography' is missing for encrypted file vault operations. "
                    "Install it via 'pip install cryptography' or configure the OS keyring."
                ) from exc

            key = self._derive_key(salt)
            aesgcm = AESGCM(key)
            plaintext = json.dumps(data, indent=2).encode("utf-8")
            ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=MAGIC_HEADER)

            payload = MAGIC_HEADER + salt + nonce + ciphertext

            temp_path = self.path.with_suffix(f".tmp.{secrets.token_hex(4)}")
            try:
                temp_path.write_bytes(payload)
                _enforce_private_permissions(temp_path)
                temp_path.replace(self.path)
                _enforce_private_permissions(self.path)
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass

    def get_credential(self, provider: str) -> dict[str, Any] | None:
        with self._lock:
            data = self._load_all()
            return data.get(provider.lower().strip())

    def set_credential(self, provider: str, token_data: dict[str, Any]) -> None:
        norm_provider = provider.lower().strip()
        with self._lock:
            try:
                data = self._load_all()
            except ValueError:
                self.recover_corrupted(backup=True)
                data = {}
            rec = dict(token_data)
            rec["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            data[norm_provider] = rec
            self._save_all(data)

    def delete_credential(self, provider: str) -> bool:
        norm_provider = provider.lower().strip()
        with self._lock:
            try:
                data = self._load_all()
            except ValueError:
                return False
            if norm_provider in data:
                del data[norm_provider]
                self._save_all(data)
                return True
            return False

    def list_providers(self) -> list[str]:
        with self._lock:
            try:
                data = self._load_all()
                return sorted(data.keys())
            except ValueError:
                return []

    def recover_corrupted(self, backup: bool = True) -> Path | None:
        """Safely recover from a corrupted vault file by backing it up or purging it."""
        with self._lock:
            if not self.path.exists():
                return None
            backup_path = None
            if backup:
                timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_path = self.path.with_name(f"{self.path.name}.corrupted.{timestamp}")
                try:
                    self.path.replace(backup_path)
                except Exception:
                    self.path.unlink(missing_ok=True)
            else:
                self.path.unlink(missing_ok=True)
            return backup_path


class KeyringVault:
    """OS-native credential storage using the Python keyring library.

    Targets Windows Credential Manager, macOS Keychain, and Linux Secret Service.
    """

    def __init__(self, service_name: str = HARNESS_KEYRING_SERVICE) -> None:
        self.service_name = service_name
        self._keyring = None
        self._lock = threading.RLock()
        try:
            import keyring

            self._keyring = keyring
        except ImportError:
            pass

    def __repr__(self) -> str:
        return f"<KeyringVault service={self.service_name}>"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def is_available(self) -> bool:
        if self._keyring is None:
            return False
        try:
            backend = self._keyring.get_keyring()
            if backend is None:
                return False
            name = backend.__class__.__name__
            # Reject fail/null backends
            if "fail" in name.lower() or "null" in name.lower():
                return False
            return True
        except Exception:
            return False

    def _get_providers_index(self) -> list[str]:
        if not self.is_available:
            return []
        try:
            raw = self._keyring.get_password(self.service_name, HARNESS_PROVIDERS_KEY)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return []

    def _set_providers_index(self, providers: list[str]) -> None:
        if not self.is_available:
            return
        try:
            clean = sorted(list(set(providers)))
            self._keyring.set_password(self.service_name, HARNESS_PROVIDERS_KEY, json.dumps(clean))
        except Exception:
            pass

    def get_credential(self, provider: str) -> dict[str, Any] | None:
        if not self.is_available:
            return None
        norm_provider = provider.lower().strip()
        with self._lock:
            try:
                raw = self._keyring.get_password(self.service_name, norm_provider)
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                raise RuntimeError(f"Keyring read error for provider '{provider}': {exc}") from exc
        return None

    def set_credential(self, provider: str, token_data: dict[str, Any]) -> None:
        if not self.is_available:
            raise RuntimeError("Keyring is not available on this platform")
        norm_provider = provider.lower().strip()
        rec = dict(token_data)
        rec["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        with self._lock:
            try:
                self._keyring.set_password(self.service_name, norm_provider, json.dumps(rec))
                # Update index
                providers = self._get_providers_index()
                if norm_provider not in providers:
                    providers.append(norm_provider)
                    self._set_providers_index(providers)
            except Exception as exc:
                raise RuntimeError(f"Keyring write error for provider '{provider}': {exc}") from exc

    def delete_credential(self, provider: str) -> bool:
        if not self.is_available:
            return False
        norm_provider = provider.lower().strip()
        with self._lock:
            try:
                self._keyring.delete_password(self.service_name, norm_provider)
                providers = self._get_providers_index()
                if norm_provider in providers:
                    providers.remove(norm_provider)
                    self._set_providers_index(providers)
                return True
            except Exception:
                # Keyring raises PasswordDeleteError if not found
                return False

    def list_providers(self) -> list[str]:
        with self._lock:
            return self._get_providers_index()


class UniversalVault:
    """Unified vault manager with automatic fallback between OS Keyring and Encrypted File Vault."""

    def __init__(
        self,
        service_name: str = HARNESS_KEYRING_SERVICE,
        vault_path: Path | str | None = None,
        passphrase: str | None = None,
        force_file_vault: bool = False,
    ) -> None:
        self.keyring_vault = KeyringVault(service_name=service_name)
        self.file_vault = EncryptedFileVault(vault_path=vault_path, passphrase=passphrase)
        self.force_file_vault = force_file_vault or (os.environ.get("HARNESS_FORCE_FILE_VAULT", "").lower() in ("1", "true"))

    def __repr__(self) -> str:
        return f"<UniversalVault backend={self.active_backend_name}>"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def active_backend_name(self) -> str:
        if self.force_file_vault:
            return "encrypted_file"
        try:
            if self.keyring_vault.is_available:
                backend = self.keyring_vault._keyring.get_keyring()
                return f"keyring:{backend.__class__.__name__}"
        except Exception:
            pass
        return "encrypted_file"

    def get_credential(self, provider: str) -> dict[str, Any] | None:
        if not self.force_file_vault:
            try:
                if self.keyring_vault.is_available:
                    cred = self.keyring_vault.get_credential(provider)
                    if cred is not None:
                        return cred
            except Exception:
                pass
        return self.file_vault.get_credential(provider)

    def set_credential(self, provider: str, token_data: dict[str, Any]) -> None:
        if not self.force_file_vault:
            try:
                if self.keyring_vault.is_available:
                    self.keyring_vault.set_credential(provider, token_data)
                    return
            except Exception:
                pass
        self.file_vault.set_credential(provider, token_data)

    def delete_credential(self, provider: str) -> bool:
        deleted_kr = False
        if not self.force_file_vault:
            try:
                if self.keyring_vault.is_available:
                    deleted_kr = self.keyring_vault.delete_credential(provider)
            except Exception:
                pass
        deleted_file = self.file_vault.delete_credential(provider)
        return deleted_kr or deleted_file

    def list_providers(self) -> list[str]:
        providers = set()
        if not self.force_file_vault:
            try:
                if self.keyring_vault.is_available:
                    providers.update(self.keyring_vault.list_providers())
            except Exception:
                pass
        try:
            providers.update(self.file_vault.list_providers())
        except Exception:
            pass
        return sorted(list(providers))


_GLOBAL_VAULT: UniversalVault | None = None


def get_vault(force_file_vault: bool = False) -> UniversalVault:
    """Return the global UniversalVault instance."""
    global _GLOBAL_VAULT
    if _GLOBAL_VAULT is None or force_file_vault:
        _GLOBAL_VAULT = UniversalVault(force_file_vault=force_file_vault)
    return _GLOBAL_VAULT
