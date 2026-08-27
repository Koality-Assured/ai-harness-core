"""Inspect reusable qmd state without creating or refreshing an index.

tags: [qmd]
routing_hints: [preflight, index, onboarding, safety]

The default path only reads filesystem metadata. ``--probe-cli`` additionally
runs ``qmd status``; it never calls collection add, init, update, or embed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
try:
    from paths import REPO_ROOT as DEFAULT_ROOT
except ImportError:
    DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def resolve_qmd() -> str | None:
    """Return an executable qmd path, preferring the Windows cmd shim."""
    if sys.platform == "win32":
        return shutil.which("qmd.cmd") or shutil.which("qmd.exe") or shutil.which("qmd")
    return shutil.which("qmd")


def candidate_index_paths(
    *,
    environ: dict[str, str] | None = None,
    home: Path | None = None,
    repo_root: Path | None = None,
) -> list[Path]:
    """Return documented and conventional qmd cache candidates without creating them.
    
    Project-local `.qmd/index.sqlite` is checked first to support isolated multi-harness databases.
    """
    env = os.environ if environ is None else environ
    user_home = Path.home() if home is None else home
    root = DEFAULT_ROOT if repo_root is None else repo_root
    candidates: list[Path] = []
    if root:
        candidates.append(root / ".qmd" / "index.sqlite")
    if cache_override := env.get("QMD_CACHE_DIR"):
        override = Path(cache_override)
        candidates.append(override if override.suffix == ".sqlite" else override / "index.sqlite")
    if xdg_cache := env.get("XDG_CACHE_HOME"):
        candidates.append(Path(xdg_cache) / "qmd" / "index.sqlite")
    candidates.append(user_home / ".cache" / "qmd" / "index.sqlite")
    if local_app_data := env.get("LOCALAPPDATA"):
        candidates.append(Path(local_app_data) / "qmd" / "index.sqlite")

    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def index_observations(paths: list[Path]) -> list[dict[str, Any]]:
    """Return metadata only; do not open SQLite or create WAL files."""
    observations: list[dict[str, Any]] = []
    for path in paths:
        observation: dict[str, Any] = {"path": str(path), "exists": False}
        try:
            stat = path.stat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            observation["error"] = f"{type(exc).__name__}: {exc}"
        else:
            observation.update({"exists": True, "bytes": stat.st_size, "readable": os.access(path, os.R_OK)})
        observations.append(observation)
    return observations


def config_candidates(
    *,
    environ: dict[str, str] | None = None,
    home: Path | None = None,
    repo_root: Path | None = None,
) -> list[Path]:
    """Locate only known qmd config paths; the function never creates config."""
    env = os.environ if environ is None else environ
    user_home = Path.home() if home is None else home
    root = DEFAULT_ROOT if repo_root is None else repo_root
    paths: list[Path] = []
    if root:
        paths.append(root / ".qmd" / "index.yml")
        paths.append(root / ".qmd" / "index.yaml")
    if xdg_config := env.get("XDG_CONFIG_HOME"):
        paths.append(Path(xdg_config) / "qmd" / "index.yml")
    paths.append(user_home / ".config" / "qmd" / "index.yml")
    if local_app_data := env.get("LOCALAPPDATA"):
        paths.append(Path(local_app_data) / "qmd" / "index.yml")
    return list(dict.fromkeys(paths))


def inspect_qmd_hooks(paths: list[Path] | None = None) -> dict[str, Any]:
    """Report possible hook directives without exposing configuration values.

    QMD configuration can be operator-global. A broad ``hook`` key scan is
    deliberately conservative: a potential match requires human inspection
    before a setup operation mutates that configuration.
    """
    observations: list[dict[str, Any]] = []
    for path in paths if paths is not None else config_candidates():
        item: dict[str, Any] = {"path": str(path), "exists": path.is_file(), "hook_lines": []}
        if not path.is_file():
            observations.append(item)
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        else:
            item["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            item["hook_lines"] = [
                line_no
                for line_no, line in enumerate(text.splitlines(), start=1)
                if "hook" in line.lower() and not line.lstrip().startswith("#")
            ]
        observations.append(item)
    return {
        "config": observations,
        "potential_hooks": [item["path"] for item in observations if item.get("hook_lines")],
        "inspection_errors": [item["path"] for item in observations if item.get("error")],
    }


def probe_status(qmd: str, *, timeout: int) -> dict[str, Any]:
    """Run the qmd status probe and retain a bounded diagnostic tail."""
    try:
        proc = subprocess.run(
            [qmd, "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"attempted": True, "ok": False, "error": f"timeout after {timeout}s"}
    detail = (proc.stderr or proc.stdout).strip()
    return {
        "attempted": True,
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "diagnostic_tail": detail[-1200:],
    }


def classify(
    *, indexes: list[dict[str, Any]], qmd: str | None, probe: dict[str, Any] | None, config_errors: bool = False
) -> str:
    """Classify state without inferring that a failed process damaged the index."""
    has_index = any(item.get("exists") for item in indexes)
    if not has_index:
        return "missing"
    if config_errors:
        return "inaccessible_sandbox_or_permissions"
    if qmd is None:
        return "cli_unavailable"
    if probe is None:
        return "existing_unprobed"
    if probe.get("ok"):
        return "healthy_reusable"
    text = str(probe.get("diagnostic_tail") or probe.get("error") or "").lower()
    if "sqlite_cantopen" in text or "unable to open database" in text or "permission" in text:
        return "inaccessible_sandbox_or_permissions"
    return "inaccessible_or_unhealthy"


def build_report(*, probe_cli: bool, inspect_hooks: bool, timeout: int) -> dict[str, Any]:
    """Build a no-mutation preflight report."""
    indexes = index_observations(candidate_index_paths())
    qmd = resolve_qmd()
    probe = probe_status(qmd, timeout=timeout) if probe_cli and qmd else None
    hooks = inspect_qmd_hooks() if inspect_hooks else None
    state = classify(
        indexes=indexes,
        qmd=qmd,
        probe=probe,
        config_errors=bool(hooks and hooks["inspection_errors"]),
    )
    if state in {"healthy_reusable", "existing_unprobed"}:
        next_step = "Reuse the existing index; do not run setup or refresh."
    else:
        next_step = "Resolve accessibility or verify a clean host before any explicit setup action."
    return {
        "operation": "qmd_preflight",
        "mutating_commands_run": [],
        "qmd": qmd,
        "indexes": indexes,
        "cli_probe": probe,
        "state": state,
        "hook_inspection": hooks,
        "next_step": next_step,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-cli", action="store_true", help="Explicitly run read-oriented `qmd status`")
    parser.add_argument("--inspect-hooks", action="store_true", help="Inspect known qmd config paths for hook keys")
    parser.add_argument("--timeout", type=int, default=15, help="qmd status timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    report = build_report(probe_cli=args.probe_cli, inspect_hooks=args.inspect_hooks, timeout=args.timeout)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"qmd state: {report['state']}")
        for item in report["indexes"]:
            size = f", {item['bytes']} bytes" if item.get("exists") else ""
            print(f"- {item['path']}: {'present' if item.get('exists') else 'missing'}{size}")
        if report["cli_probe"]:
            print(f"- qmd status: {'ok' if report['cli_probe'].get('ok') else 'failed'}")
        if report["hook_inspection"]:
            hooks = report["hook_inspection"]["potential_hooks"]
            print(f"- config hook directives: {len(hooks)} candidate file(s)")
        print(report["next_step"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
