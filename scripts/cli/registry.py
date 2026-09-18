"""Harness registry manager for multi-harness discovery and switching.

Manages ~/.harness/config.json (or HARNESS_CONFIG_PATH) to track local
domain harnesses, active harness selection, and dynamic workspace discovery.

tags: [harness, cli, registry, multi-harness, switcher]
routing_hints: [harness, registry, switch, scan, list, register, deregister]
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

# Ensure _lib and scripts are in sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_LIB_DIR = _SCRIPTS_DIR / "_lib"
for _p in (str(_LIB_DIR), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from areas import load_area_ids
except ImportError:
    load_area_ids = None

DEFAULT_REGISTRY_DIR = Path.home() / ".harness"
DEFAULT_CONFIG_PATH = DEFAULT_REGISTRY_DIR / "config.json"

KNOWN_DOMAINS: dict[str, str] = {
    "ai-router": "General Orchestrator & AI Router",
    "ai-harness-core": "Domain-Agnostic Core Baseline Engine",
    "art-router": "Digital Art & Creative Asset Generation",
    "legal-router": "Legal Document Analysis & Regulatory Compliance",
    "ui-ux-router": "UI/UX Design Systems & Interface Synthesis",
    "financial-advisement-router": "Quantitative Finance & Advisement Engine",
    "game-dev-router": "Game Systems Simulation & Logic Generation",
    "knockoutbeauty": "E-Commerce Brand & Catalog Optimization",
}


def _enforce_private_permissions(path: Path) -> None:
    """Enforce strict user-only read/write permissions on secret and config files."""
    if not path.exists():
        return
    if os.name == "nt":
        user = os.environ.get("USERNAME")
        if user:
            try:
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


def get_config_path() -> Path:
    """Return the active harness registry configuration file path."""
    env_path = os.environ.get("HARNESS_CONFIG_PATH")
    if env_path:
        return Path(env_path).resolve()
    return DEFAULT_CONFIG_PATH.resolve()


RESERVED_SLUGS = {
    "con", "prn", "aux", "nul",
    "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
}


def slugify_id(text: str) -> str:
    """Convert text into a kebab-case identifier."""
    slug = text.strip().lower().replace("_", "-")
    slug = re.sub(r"[^a-z0-9\-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        return "harness"
    if slug in RESERVED_SLUGS:
        return f"harness-{slug}"
    return slug


def infer_harness_domain(repo_root: Path) -> str:
    """Infer friendly domain description from repository markers or configuration."""
    name_lower = repo_root.name.lower()
    if name_lower in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[name_lower]

    cfg_file = repo_root / "config" / "harness.config.json"
    if cfg_file.is_file():
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            if isinstance(cfg, dict):
                if cfg.get("domain"):
                    return str(cfg["domain"])
                if cfg.get("description"):
                    return str(cfg["description"])
        except Exception:
            pass

    # Inspect README or AGENTS title
    agents_file = repo_root / "AGENTS.md"
    if agents_file.is_file():
        try:
            for line in agents_file.read_text(encoding="utf-8").splitlines()[:5]:
                if line.startswith("# "):
                    title = line[2:].strip()
                    if title:
                        return title
        except Exception:
            pass

    # Fallback to humanized directory name
    parts = repo_root.name.replace("-", " ").replace("_", " ").split()
    return " ".join(p.capitalize() for p in parts)


def inspect_harness(repo_path: Path) -> dict[str, Any]:
    """Inspect a local repository and extract live metadata (branch, claims, areas)."""
    resolved = repo_path.resolve()
    exists = resolved.is_dir()

    info: dict[str, Any] = {
        "path": str(resolved),
        "exists": exists,
        "is_git": False,
        "branch": "(unknown)",
        "status": "MISSING" if not exists else "UNKNOWN",
        "worktrees_count": 0,
        "claims_count": 0,
        "areas_count": 0,
        "domain": infer_harness_domain(resolved) if exists else "Unknown",
    }

    if not exists:
        return info

    git_dir = resolved / ".git"
    info["is_git"] = git_dir.exists()

    if info["is_git"]:
        # Query branch
        try:
            proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=resolved,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=3,
                check=False,
            )
            branch = proc.stdout.strip()
            if branch:
                info["branch"] = branch
            else:
                # Detached HEAD check
                proc_head = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=resolved,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=3,
                    check=False,
                )
                commit = proc_head.stdout.strip()
                info["branch"] = f"detached({commit})" if commit else "(unknown)"
        except subprocess.TimeoutExpired:
            info["branch"] = "(timeout)"
        except Exception:
            info["branch"] = "(error)"

        # Query git cleanliness
        try:
            proc_status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=resolved,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=3,
                check=False,
            )
            info["status"] = "DIRTY" if proc_status.stdout.strip() else "CLEAN"
        except subprocess.TimeoutExpired:
            info["status"] = "(timeout)"
        except Exception:
            info["status"] = "UNKNOWN"

    # Count claims & worktrees
    claims_dir = resolved / "scratch" / "worktrees"
    if claims_dir.is_dir():
        try:
            claims = list(claims_dir.glob("*.claim.json"))
            info["claims_count"] = len(claims)
            wts = [d for d in claims_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
            info["worktrees_count"] = len(wts)
        except Exception:
            pass

    # Count areas
    if load_area_ids:
        try:
            areas = load_area_ids(resolved)
            info["areas_count"] = len(areas)
        except Exception:
            pass

    return info


class HarnessRegistry:
    """Thread-safe registry for managing local domain harnesses and switcher configuration."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.path = Path(config_path).resolve() if config_path else get_config_path()
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"<HarnessRegistry path={self.path}>"

    def _default_data(self) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "version": "1.0.0",
            "active_harness": None,
            "harnesses": {},
        }

    def _load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.is_file():
                return self._default_data()

            try:
                raw = self.path.read_text(encoding="utf-8").strip()
                if not raw:
                    return self._default_data()
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("Registry JSON root must be an object")
                if "harnesses" not in data or not isinstance(data["harnesses"], dict):
                    data["harnesses"] = {}
                if "active_harness" not in data:
                    data["active_harness"] = None
                return data
            except Exception as exc:
                # Corrupted registry recovery
                ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_path = self.path.with_name(f"{self.path.name}.corrupted.{ts}")
                try:
                    shutil.copy2(self.path, backup_path)
                    print(
                        f"warning: corrupted harness registry config at {self.path} ({exc}). "
                        f"Backed up to {backup_path.name} and initialized clean registry.",
                        file=sys.stderr,
                    )
                except Exception:
                    pass
                fresh = self._default_data()
                self._save(fresh)
                return fresh

    def _save(self, data: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _enforce_private_dir_permissions(self.path.parent)

            tmp_path = self.path.with_name(f"{self.path.name}.tmp.{os.getpid()}.{secrets.token_hex(4)}")
            payload = json.dumps(data, indent=2)
            try:
                tmp_path.write_text(payload, encoding="utf-8")
                _enforce_private_permissions(tmp_path)

                # Retry replace for Windows file lock contention
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        tmp_path.replace(self.path)
                        break
                    except PermissionError:
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(0.05)

                _enforce_private_permissions(self.path)
            finally:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass

    def register(
        self,
        path: Path | str,
        name: str | None = None,
        domain: str | None = None,
        make_active: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Register a local repository checkout as a known domain harness."""
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Cannot register harness: directory '{resolved}' does not exist.")
        if not resolved.is_dir():
            raise NotADirectoryError(f"Cannot register harness: '{resolved}' is not a directory.")

        # Check repository markers
        is_git = (resolved / ".git").exists()
        has_areas = (resolved / "routing" / "areas.yaml").is_file()
        has_config = (resolved / "config" / "harness.config.json").is_file()
        has_agents = (resolved / "AGENTS.md").is_file()

        if not (is_git or has_areas or has_config or has_agents) and not force:
            raise ValueError(
                f"Directory '{resolved}' does not appear to be a git repository or domain harness "
                "(missing .git, routing/areas.yaml, or AGENTS.md). Pass force=True to register anyway."
            )

        with self._lock:
            data = self._load()
            harnesses: dict[str, dict[str, Any]] = data.get("harnesses", {})

            # Check if this exact path is already registered under an existing ID
            existing_id = None
            resolved_str = str(resolved).lower() if os.name == "nt" else str(resolved)
            for hid, hdata in harnesses.items():
                target_str = str(Path(hdata.get("path", "")).resolve())
                if (target_str.lower() if os.name == "nt" else target_str) == resolved_str:
                    existing_id = hid
                    break

            hid = existing_id or slugify_id(name or resolved.name)

            # Avoid ID collisions if a different repo used this slug
            if not existing_id and hid in harnesses:
                counter = 2
                while f"{hid}-{counter}" in harnesses:
                    counter += 1
                hid = f"{hid}-{counter}"

            now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
            detected_domain = domain or infer_harness_domain(resolved)
            friendly_name = name or harnesses.get(hid, {}).get("name") or resolved.name

            record = {
                "id": hid,
                "name": friendly_name,
                "path": str(resolved),
                "domain": detected_domain,
                "registered_at": harnesses.get(hid, {}).get("registered_at") or now_iso,
                "last_switched_at": harnesses.get(hid, {}).get("last_switched_at"),
            }

            harnesses[hid] = record
            data["harnesses"] = harnesses

            if make_active or not data.get("active_harness"):
                data["active_harness"] = hid
                record["last_switched_at"] = now_iso

            self._save(data)
            return record

    def deregister(self, id_or_path: str) -> bool:
        """Deregister a harness by ID or file path."""
        with self._lock:
            data = self._load()
            harnesses: dict[str, dict[str, Any]] = data.get("harnesses", {})

            target_id = self._resolve_id(id_or_path, harnesses)
            if not target_id or target_id not in harnesses:
                return False

            del harnesses[target_id]
            data["harnesses"] = harnesses

            if data.get("active_harness") == target_id:
                # Switch active to another harness or None
                data["active_harness"] = next(iter(harnesses.keys()), None)

            self._save(data)
            return True

    def _resolve_id(self, id_or_path: str, harnesses: dict[str, dict[str, Any]]) -> str | None:
        if id_or_path in harnesses:
            return id_or_path

        # Case-insensitive ID lookup
        id_lower = id_or_path.lower()
        for hid in harnesses:
            if hid.lower() == id_lower:
                return hid

        # Path resolution lookup
        try:
            target_path = Path(id_or_path).resolve()
            target_str = str(target_path).lower() if os.name == "nt" else str(target_path)
            for hid, hdata in harnesses.items():
                p = Path(hdata.get("path", "")).resolve()
                p_str = str(p).lower() if os.name == "nt" else str(p)
                if p_str == target_str:
                    return hid
        except Exception:
            pass

        return None

    def get_harness(self, id_or_path: str) -> dict[str, Any] | None:
        """Retrieve stored harness record by ID or path."""
        with self._lock:
            data = self._load()
            harnesses = data.get("harnesses", {})
            target_id = self._resolve_id(id_or_path, harnesses)
            if target_id and target_id in harnesses:
                return dict(harnesses[target_id])
            return None

    def get_active_harness(self) -> dict[str, Any] | None:
        """Return the active harness record, or None if none active."""
        with self._lock:
            data = self._load()
            active_id = data.get("active_harness")
            if not active_id:
                return None
            harnesses = data.get("harnesses", {})
            if active_id in harnesses:
                return dict(harnesses[active_id])
            return None

    def switch(self, id_or_path: str) -> dict[str, Any]:
        """Set the active harness to the specified ID or path."""
        with self._lock:
            data = self._load()
            harnesses = data.get("harnesses", {})
            target_id = self._resolve_id(id_or_path, harnesses)
            if not target_id or target_id not in harnesses:
                raise KeyError(f"Harness '{id_or_path}' is not registered in the catalog.")

            record = harnesses[target_id]
            harness_path = Path(record["path"])
            if not harness_path.exists():
                raise FileNotFoundError(
                    f"Registered path for harness '{target_id}' does not exist on disk: {harness_path}"
                )
            if not harness_path.is_dir():
                raise NotADirectoryError(
                    f"Registered path for harness '{target_id}' is not a directory: {harness_path}"
                )

            data["active_harness"] = target_id
            now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
            record["last_switched_at"] = now_iso
            harnesses[target_id] = record
            data["harnesses"] = harnesses
            self._save(data)
            return record

    def list_harnesses(self) -> list[dict[str, Any]]:
        """Return list of all registered harnesses with live inspection metadata."""
        with self._lock:
            data = self._load()
            harnesses = data.get("harnesses", {})
            active_id = data.get("active_harness")

            results = []
            for hid, hdata in sorted(harnesses.items(), key=lambda x: x[0]):
                entry = dict(hdata)
                entry["is_active"] = (hid == active_id)

                # Augment with live git status
                live_info = inspect_harness(Path(entry["path"]))
                entry["live"] = live_info
                results.append(entry)

            return results

    def scan_siblings(
        self,
        parent_dir: Path | str | None = None,
        auto_register: bool = True,
    ) -> list[dict[str, Any]]:
        """Auto-discover sibling harness repositories and optionally register them."""
        if parent_dir:
            scan_root = Path(parent_dir).resolve()
        else:
            # Default to parent of current REPO_ROOT / cwd
            scan_root = _SCRIPTS_DIR.parents[0].parent.resolve()

        if not scan_root.is_dir():
            return []

        discovered: list[dict[str, Any]] = []

        try:
            entries = sorted(scan_root.iterdir(), key=lambda p: p.name.lower())
        except Exception:
            return []

        for item in entries:
            if not item.is_dir() or item.name.startswith("."):
                continue

            # Check harness markers
            is_git = (item / ".git").exists()
            has_areas = (item / "routing" / "areas.yaml").is_file()
            has_config = (item / "config" / "harness.config.json").is_file()
            has_agents = (item / "AGENTS.md").is_file()

            # Must be a git repo and possess at least one router/harness marker
            if is_git and (has_areas or has_config or has_agents):
                live_meta = inspect_harness(item)
                item_info = {
                    "path": str(item),
                    "name": item.name,
                    "domain": live_meta["domain"],
                    "branch": live_meta["branch"],
                    "status": live_meta["status"],
                }

                if auto_register:
                    reg_record = self.register(
                        path=item,
                        name=item.name,
                        domain=live_meta["domain"],
                        make_active=False,
                    )
                    item_info["id"] = reg_record["id"]
                    item_info["registered"] = True
                else:
                    item_info["id"] = slugify_id(item.name)
                    item_info["registered"] = False

                discovered.append(item_info)

        return discovered


_REGISTRY_INSTANCE: HarnessRegistry | None = None


def get_registry() -> HarnessRegistry:
    """Return singleton HarnessRegistry instance for current configuration path."""
    global _REGISTRY_INSTANCE
    current_path = get_config_path()
    if _REGISTRY_INSTANCE is None or _REGISTRY_INSTANCE.path != current_path:
        _REGISTRY_INSTANCE = HarnessRegistry(config_path=current_path)
    return _REGISTRY_INSTANCE
