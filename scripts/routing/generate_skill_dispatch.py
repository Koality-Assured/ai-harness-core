"""Generate routing/skill-dispatch.md from skill frontmatter.

tags: [routing, ai-tooling]
routing_hints: [skills, dispatch, catalog]

Thin wrapper around generate_routing_index.py (same writer, also refreshes area-map).
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from generate_routing_index import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
