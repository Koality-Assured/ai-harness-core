#!/usr/bin/env bash
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"
if ! command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi
exec "$PYTHON_BIN" "${SCRIPT_DIR}/scripts/cli/harness.py" "$@"
