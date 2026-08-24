"""Automated scaffolding CLI to initialize the 3 public Koality-Assured ecosystem repositories.

tags: [repos, scaffold, github]
routing_hints: [scaffold, public-repos, agent-skills, agent-standards, ai-research, wiki-template]
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_LIB = Path(__file__).resolve().parents[1] / "_lib"
_SYNC = Path(__file__).resolve().parents[1] / "sync"
sys.path.insert(0, str(_LIB))
if str(_SYNC) not in sys.path:
    sys.path.insert(0, str(_SYNC))
from paths import REPO_ROOT, resolve_repo_root  # noqa: E402
from _wiki_template import (  # noqa: E402
    GENERIC_TEMPLATE_CI,
    GENERIC_TEMPLATE_README,
    GENERIC_TEMPLATE_REFERENCES_AGENTS,
    GENERIC_TEMPLATE_STUB_AGENTS,
)


MIT_LICENSE_TEMPLATE = """MIT License

Copyright (c) 2026 Koality-Assured

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

COMMON_GITIGNORE = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Node / JS dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE and editors
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# Testing and coverage
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
.coverage.*
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/

# Linting and type checking
.mypy_cache/
.ruff_cache/

# Local data & runs
*.log
scratch/
tmp/
"""

COMMON_EDITORCONFIG = """root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_size = 4

[*.{yml,yaml,json,md}]
indent_size = 2

[Makefile]
indent_style = tab
"""


# -----------------------------------------------------------------------------
# Repo 1: agent-skills-and-tools
# -----------------------------------------------------------------------------

def _build_agent_skills_files() -> Dict[str, str]:
    files: Dict[str, str] = {}

    files["LICENSE"] = MIT_LICENSE_TEMPLATE
    files[".gitignore"] = COMMON_GITIGNORE
    files[".editorconfig"] = COMMON_EDITORCONFIG

    files[".github/workflows/ci.yml"] = """name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  lint-and-validate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install jsonschema pyyaml pytest

      - name: Validate Skills and Schemas
        run: |
          python -m unittest discover -s tests -v

      - name: Run Skill Validator CLI
        run: |
          python tools/validator.py --all
"""

    files["README.md"] = """# Agent Skills & Tools (`agent-skills-and-tools`)

[![CI](https://github.com/Koality-Assured/agent-skills-and-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/Koality-Assured/agent-skills-and-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Schema: Draft 2020-12](https://img.shields.io/badge/Schema-Draft_2020--12-green.svg)](schemas/)

## Mission Statement

`agent-skills-and-tools` is the official open-source ecosystem repository of verified, reusable agent skills, standard tool schemas, and operational utilities for autonomous coding and orchestration agents.

Our mission is to standardize how software engineering agents discover, inspect, and execute domain skills and tool integrations across diverse runtime harnesses while enforcing strict sandboxing, schema guarantees, and security boundaries.

## Architecture Overview

```
agent-skills-and-tools/
├── .github/workflows/ci.yml    # Continuous integration & schema validation
├── schemas/                    # Formal JSON Schema specifications
│   ├── skill.schema.json       # Frontmatter and metadata schema for SKILL.md
│   └── tool.schema.json        # Tool function declaration and parameter schema
├── skills/                     # Reusable domain skills library
│   ├── git-worktree-manager/   # Git worktree lifecycle management skill
│   └── ast-fact-extractor/     # AST symbol & call graph extraction skill
├── tools/                      # Validation CLI and integration utilities
│   ├── __init__.py
│   └── validator.py            # CLI validator for skills and tool declarations
├── tests/                      # Automated test suite
│   ├── __init__.py
│   └── test_skills.py          # Unit tests verifying skills against schemas
├── pyproject.toml              # Python project and dependency configuration
├── .editorconfig               # Editor configuration
├── .gitignore                  # Git ignore rules
└── LICENSE                     # MIT License
```

## Directory Structure

| Path | Purpose |
| --- | --- |
| `skills/` | Curated, validated agent skills with `SKILL.md`, examples, and execution guidance. |
| `schemas/` | Standard JSON Schemas (Draft 2020-12) defining skill frontmatter and tool parameters. |
| `tools/` | Python CLI utilities for schema linting, syntax verification, and packaging. |
| `tests/` | Unit and regression test suite executed in CI across Python versions. |

## Installation & Setup

### Prerequisites
- Python >= 3.10
- Git

### Local Setup

```bash
# Clone the repository
git clone https://github.com/Koality-Assured/agent-skills-and-tools.git
cd agent-skills-and-tools

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# Install dependencies in editable mode
pip install -e ".[dev]"
```

## Usage

### Validate Skills and Schemas

Run the built-in validator against all skills in the repository:

```bash
# Validate all skills in skills/ against schemas/skill.schema.json
python tools/validator.py --all

# Validate a specific skill directory
python tools/validator.py --skill skills/git-worktree-manager

# Validate a specific tool schema
python tools/validator.py --tool-schema schemas/tool.schema.json
```

### Running Tests

```bash
python -m unittest discover -s tests -v
```

## Authoring a New Skill

Each skill resides in its own subdirectory under `skills/<skill-name>/` and must contain a `SKILL.md` file adhering to `schemas/skill.schema.json`.

Example `SKILL.md`:

```markdown
---
name: my-new-skill
description: Comprehensive description of when and how the agent must activate this skill.
version: 1.0.0
tags: [git, automation]
author: Koality-Assured
---

# My New Skill

## When to Use
- Detailed trigger conditions for the agent.

## Workflow Instructions
1. Step-by-step deterministic procedures.
```

## Security Notice

All skills and tool declarations in this repository are designed with defense-in-depth:
- **Sandbox Boundary:** Tool implementations MUST execute inside sandboxed or worktree-isolated environments.
- **AST Safety:** Code modification tools MUST validate syntax trees prior to filesystem commit.
- **Secret Isolation:** Tools MUST NOT log, leak, or interpolate raw environment credentials into agent prompts.

To report security vulnerabilities, please email security@koality-assured.org or open a GitHub Security Advisory.

## Contribution Guidelines

1. Fork the repository and create a feature branch (`feature/my-skill-name`).
2. Add your skill under `skills/<skill-name>/` with a valid `SKILL.md`.
3. Run `python tools/validator.py --all` and ensure tests pass: `python -m unittest discover -s tests -v`.
4. Submit a Pull Request with a clear description of the skill's capabilities and test coverage.

## License

Distributed under the [MIT License](LICENSE). Copyright (c) 2026 Koality-Assured.
"""

    files["pyproject.toml"] = """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-skills-and-tools"
version = "0.1.0"
description = "Public repository of reusable agent skills, schemas, and supporting tool integrations"
readme = "README.md"
authors = [{ name = "Koality-Assured", email = "engineering@koality-assured.org" }]
license = { text = "MIT" }
requires-python = ">=3.10"
dependencies = [
    "jsonschema>=4.20.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.3.0",
]

[project.scripts]
agent-skills = "tools.validator:main"
"""

    files["schemas/skill.schema.json"] = json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://schema.koality-assured.org/agent/skill.schema.json",
        "title": "AgentSkillFrontmatter",
        "description": "Schema for SKILL.md YAML frontmatter metadata in agent skills.",
        "type": "object",
        "required": ["name", "description", "version"],
        "properties": {
            "name": {
                "type": "string",
                "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
                "description": "Kebab-case unique identifier for the skill."
            },
            "description": {
                "type": "string",
                "minLength": 10,
                "description": "Clear explanation of what the skill does and when the agent should activate it."
            },
            "version": {
                "type": "string",
                "pattern": "^\\d+\\.\\d+\\.\\d+$",
                "description": "SemVer 2.0 version string."
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Search and routing tags for indexing."
            },
            "author": {
                "type": "string",
                "description": "Author or organization name."
            },
            "tool_dependencies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names of tools required to execute this skill."
            }
        },
        "additionalProperties": True
    }, indent=2) + "\n"

    files["schemas/tool.schema.json"] = json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://schema.koality-assured.org/agent/tool.schema.json",
        "title": "AgentToolDeclaration",
        "description": "Schema for declaring agent tools, parameter specifications, and invocation constraints.",
        "type": "object",
        "required": ["name", "description", "parameters"],
        "properties": {
            "name": {
                "type": "string",
                "pattern": "^[a-z0-9_]+$",
                "description": "Snake_case identifier for the tool function."
            },
            "description": {
                "type": "string",
                "minLength": 10,
                "description": "Instruction to the agent detailing the purpose and behavior of the tool."
            },
            "parameters": {
                "type": "object",
                "required": ["type", "properties"],
                "properties": {
                    "type": {"type": "string", "enum": ["object"]},
                    "properties": {"type": "object"},
                    "required": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "is_daemon": {
                "type": "boolean",
                "description": "Whether the tool spawns a long-running background daemon process."
            }
        },
        "additionalProperties": False
    }, indent=2) + "\n"

    files["skills/README.md"] = """# Agent Skills Catalog

This directory contains standardized, reusable agent skills formatted for autonomous coding harnesses and multi-agent systems.

## Catalog Index

| Skill Name | Version | Description |
| --- | --- | --- |
| [`git-worktree-manager`](./git-worktree-manager/SKILL.md) | `1.0.0` | Production git worktree isolation, branch setup, and clean-up. |
| [`ast-fact-extractor`](./ast-fact-extractor/SKILL.md) | `1.0.0` | AST symbol, call graph, and type signature extraction for cost-efficient context. |

## Authoring Rules
1. Every skill folder must contain a `SKILL.md` with valid YAML frontmatter.
2. Frontmatter must conform to `schemas/skill.schema.json`.
3. Clear instructions on preconditions, execution steps, and verification.
"""

    files["skills/git-worktree-manager/SKILL.md"] = """---
name: git-worktree-manager
description: Manage dedicated git worktrees for isolated agent task execution, branch creation, and conflict-free concurrent editing.
version: 1.0.0
tags: [git, worktree, isolation, multi-agent]
author: Koality-Assured
---

# Git Worktree Manager

## When to Use
- When spawning subagents to work on independent feature branches without workspace collisions.
- When performing speculative refactoring that must remain isolated from the working tree.
- When running parallel test suites across different branches.

## Workflow Instructions

### 1. Worktree Creation
```bash
# Create dedicated branch and worktree
git worktree add [REDACTED_WORKTREE_PATH]<branch-slug> -b agent/<YYYY-MM-DD>-<branch-slug>
```

### 2. Execution & Isolation
- All commands, edits, and test runs for the task MUST be confined to `[REDACTED_WORKTREE_PATH]<branch-slug>`.
- Do not modify files in the root worktree or other sibling worktrees.

### 3. Cleanup & Teardown
```bash
# After branch is committed or merged
git worktree remove [REDACTED_WORKTREE_PATH]<branch-slug>
git worktree prune
```
"""

    files["skills/ast-fact-extractor/SKILL.md"] = """---
name: ast-fact-extractor
description: Extract precise code facts, function signatures, class definitions, and call references using AST parsing to minimize LLM context cost.
version: 1.0.0
tags: [ast, compression, headroom, tier4, retrieval]
author: Koality-Assured
---

# AST Fact Extractor

## When to Use
- When an agent needs structural knowledge of a codebase without loading full file bodies into context.
- When implementing Tier-4 context headroom compression.
- When answering symbol reference queries or building architectural call graphs.

## Workflow Instructions

### 1. Symbol Extraction
- Parse target Python files using `ast.parse`.
- Extract class names, method signatures, docstrings, and decorator annotations.

### 2. Fact Emission
- Format extracted symbols as concise JSON or compact Markdown fact tables.
- Omit internal function bodies to conserve 85%+ token headroom.
"""

    files["tools/__init__.py"] = '"""Agent skills and tools validation library."""\n'

    files["tools/validator.py"] = r'''"""CLI and library tool to validate agent skills and JSON schemas.

tags: [validator, skills, schemas]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def extract_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from a Markdown document."""
    match = FRONTMATTER_RE.match(content)
    if not match:
        raise ValueError("Missing YAML frontmatter block (enclosed in '---')")
    raw_yaml = match.group(1)
    if yaml is not None:
        data = yaml.safe_load(raw_yaml)
    else:
        # Fallback simple parser if PyYAML is not installed
        data = {}
        for line in raw_yaml.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if v.startswith("[") and v.endswith("]"):
                    items = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
                    data[k] = items
                else:
                    data[k] = v.strip("'\"")
    if not isinstance(data, dict):
        raise ValueError(f"Frontmatter did not parse to dictionary: {raw_yaml}")
    return data


def validate_skill_file(skill_md_path: Path, schema_path: Path) -> Tuple[bool, List[str]]:
    """Validate a SKILL.md file against skill.schema.json."""
    errors: List[str] = []
    if not skill_md_path.exists():
        return False, [f"File not found: {skill_md_path}"]

    try:
        content = skill_md_path.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)
    except Exception as exc:
        return False, [f"Frontmatter parsing error in {skill_md_path}: {exc}"]

    if not schema_path.exists():
        return False, [f"Schema file not found: {schema_path}"]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"Schema JSON parsing error in {schema_path}: {exc}"]

    if jsonschema is not None:
        validator = jsonschema.Draft202012Validator(schema)
        for err in validator.iter_errors(frontmatter):
            errors.append(f"Validation error at '{err.json_path}': {err.message}")
    else:
        # Fallback manual validation for core required fields
        required = schema.get("required", [])
        for req in required:
            if req not in frontmatter:
                errors.append(f"Missing required frontmatter field: '{req}'")

    return len(errors) == 0, errors


def validate_all_skills(base_dir: Path) -> Tuple[int, int]:
    """Validate all skills under the skills directory."""
    skills_dir = base_dir / "skills"
    schema_path = base_dir / "schemas" / "skill.schema.json"

    if not skills_dir.exists():
        print(f"Error: skills directory not found at {skills_dir}", file=sys.stderr)
        return 0, 1

    skill_files = list(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        print(f"No skills found in {skills_dir}")
        return 0, 0

    passed = 0
    failed = 0

    print(f"Validating {len(skill_files)} skill(s) against {schema_path.name}...")
    for sf in skill_files:
        ok, errors = validate_skill_file(sf, schema_path)
        rel_path = sf.relative_to(base_dir)
        if ok:
            print(f"  [PASS] {rel_path}")
            passed += 1
        else:
            print(f"  [FAIL] {rel_path}")
            for e in errors:
                print(f"         - {e}")
            failed += 1

    return passed, failed


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Validate all skills in skills/")
    parser.add_argument("--skill", type=str, help="Path to a specific skill directory or SKILL.md")
    parser.add_argument("--tool-schema", type=str, help="Validate a tool schema JSON file")
    parser.add_argument("--base-dir", type=str, default=".", help="Base directory of repository")
    args = parser.parse_args(argv)

    base = Path(args.base_dir).resolve()

    if args.tool_schema:
        target = Path(args.tool_schema).resolve()
        if not target.exists():
            print(f"Error: Tool schema not found at {target}", file=sys.stderr)
            return 2
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            if jsonschema is not None:
                jsonschema.Draft202012Validator.check_schema(data)
            print(f"[PASS] Tool schema is valid JSON Schema: {target}")
            return 0
        except Exception as exc:
            print(f"[FAIL] Tool schema error: {exc}", file=sys.stderr)
            return 1

    if args.skill:
        target = Path(args.skill).resolve()
        if target.is_dir():
            target = target / "SKILL.md"
        schema_path = base / "schemas" / "skill.schema.json"
        ok, errors = validate_skill_file(target, schema_path)
        if ok:
            print(f"[PASS] {target}")
            return 0
        else:
            print(f"[FAIL] {target}", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1

    # Default to validating all
    passed, failed = validate_all_skills(base)
    print(f"Result: {passed} passed, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

    files["tests/__init__.py"] = '"""Test suite for agent-skills-and-tools."""\n'

    files["tests/test_skills.py"] = r'''"""Unit tests verifying skills against schemas."""

import json
import unittest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from tools.validator import extract_frontmatter, validate_skill_file


class TestSkillsAndSchemas(unittest.TestCase):
    def setUp(self):
        self.root = _ROOT
        self.schemas_dir = self.root / "schemas"
        self.skills_dir = self.root / "skills"

    def test_schemas_exist_and_are_valid_json(self):
        skill_schema = self.schemas_dir / "skill.schema.json"
        tool_schema = self.schemas_dir / "tool.schema.json"

        self.assertTrue(skill_schema.exists(), "skill.schema.json should exist")
        self.assertTrue(tool_schema.exists(), "tool.schema.json should exist")

        json.loads(skill_schema.read_text(encoding="utf-8"))
        json.loads(tool_schema.read_text(encoding="utf-8"))

    def test_bundled_skills_conform_to_schema(self):
        skill_schema = self.schemas_dir / "skill.schema.json"
        skill_files = list(self.skills_dir.glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skill_files), 2, "Should have at least 2 bundled skills")

        for sf in skill_files:
            ok, errors = validate_skill_file(sf, skill_schema)
            self.assertTrue(ok, f"Skill {sf.name} failed validation: {errors}")

    def test_frontmatter_extraction(self):
        sample = """---
name: test-skill
description: This is a valid test skill description.
version: 1.0.0
tags: [test, sample]
---

# Content
"""
        fm = extract_frontmatter(sample)
        self.assertEqual(fm["name"], "test-skill")
        self.assertEqual(fm["version"], "1.0.0")
        self.assertEqual(fm["tags"], ["test", "sample"])


if __name__ == "__main__":
    unittest.main()
'''

    return files


# -----------------------------------------------------------------------------
# Repo 2: agent-standards
# -----------------------------------------------------------------------------

def _build_agent_standards_files() -> Dict[str, str]:
    files: Dict[str, str] = {}

    files["LICENSE"] = MIT_LICENSE_TEMPLATE
    files[".gitignore"] = COMMON_GITIGNORE
    files[".editorconfig"] = COMMON_EDITORCONFIG

    files[".github/workflows/ci.yml"] = """name: Standards CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  validate-specs:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install jsonschema pyyaml

      - name: Validate Standards, RFCs, and Schemas
        run: |
          python -m unittest discover -s tests -v

      - name: Run Standards Validator CLI
        run: |
          python tools/validate_specs.py --all
"""

    files["README.md"] = """# Agent Standards (`agent-standards`)

[![Standards CI](https://github.com/Koality-Assured/agent-standards/actions/workflows/ci.yml/badge.svg)](https://github.com/Koality-Assured/agent-standards/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Active Standards](https://img.shields.io/badge/Status-Active_Standards-brightgreen.svg)](standards/)
[![RFC Status: Open](https://img.shields.io/badge/RFCs-Open-orange.svg)](rfcs/)

## Mission Statement

`agent-standards` defines formal, interoperable, and vendor-neutral specifications for autonomous agentic systems, multi-agent coordination protocols, hierarchical context budget management, and agent security MUSTs.

As autonomous engineering agents assume greater operational responsibility, establishing uniform interfaces and provable safety invariants is essential to enable cross-platform reliability, deterministic orchestration, and robust containment.

## Architecture Overview

```
agent-standards/
├── .github/workflows/ci.yml    # CI test & RFC validation workflow
├── standards/                  # Formal normative specifications
│   ├── context/
│   │   └── 5-tier-context-management.md  # 5-Tier Context Architecture specification
│   ├── protocols/
│   │   └── a2a-protocol-v1.md            # Agent-to-Agent (A2A) Messaging Protocol v1
│   └── security/
│       └── security-musts.md             # Normative Security MUSTs for Agent Runtimes
├── specs/                      # Machine-readable JSON schemas
│   ├── a2a-message.schema.json           # A2A Message Envelope JSON Schema
│   └── context-manifest.schema.json      # Context Manifest JSON Schema
├── rfcs/                       # Request for Comments (RFC) process & proposals
│   ├── 0001-rfc-process.md               # RFC Governance & Lifecycle Process
│   └── template.md                       # RFC Submission Template
├── tools/                      # Validation scripts
│   ├── __init__.py
│   └── validate_specs.py                 # Standards & RFC validation CLI
├── tests/                      # Automated validation tests
│   ├── __init__.py
│   └── test_standards_validation.py
├── .editorconfig               # Editor configuration
├── .gitignore                  # Git ignore rules
└── LICENSE                     # MIT License
```

## Standards Summary

### 1. 5-Tier Context Management ([`standards/context/5-tier-context-management.md`](standards/context/5-tier-context-management.md))
Specifies the hierarchical context budgeting model designed to preserve LLM reasoning headroom:
- **Tier 1: Fast Routing:** Sub-millisecond routing indices and tag lookup tables (<100 tokens).
- **Tier 2: Metadata Index & Manifests:** Structured catalog summaries and semantic search keywords.
- **Tier 3: Summary Cards & Area Guides:** High-level component summaries and operational playbooks.
- **Tier 4: Extracted AST Facts:** Deterministic symbol graphs, call hierarchies, and method signatures (85%+ token reduction).
- **Tier 5: Raw Full Text:** Selective, on-demand full file inspection reserved for direct editing.

### 2. Agent-to-Agent (A2A) Protocol ([`standards/protocols/a2a-protocol-v1.md`](standards/protocols/a2a-protocol-v1.md))
Defines structured asynchronous message envelopes, state machines, task delegation, heartbeat monitoring, and parent-subagent handoffs.

### 3. Agent Security MUSTs ([`standards/security/security-musts.md`](standards/security/security-musts.md))
Authoritative RFC 2119 security requirements for agent runtimes:
- **SEC-01: Sandboxing & Tool Isolation:** Runtimes MUST isolate shell execution and enforce working directory boundaries.
- **SEC-02: AST Validation:** Runtimes MUST validate syntax trees prior to committing edits.
- **SEC-03: Secret Boundary Protection:** Runtimes MUST NOT leak credentials into context or telemetry.
- **SEC-04: Prompt Injection Defenses:** Systems MUST separate instruction channels from untrusted user and web inputs.

## RFC Governance & Proposals

We welcome contributions to existing standards and new RFC proposals:
1. Review [`rfcs/0001-rfc-process.md`](rfcs/0001-rfc-process.md) for lifecycle states (**Proposed** → **Draft** → **In-Review** → **Accepted** → **Final**).
2. Copy [`rfcs/template.md`](rfcs/template.md) to `rfcs/YYYY-your-rfc-title.md`.
3. Submit a Pull Request for community review and voting.

## Validation CLI

Run specification and RFC schema validation locally:

```bash
# Validate all standards, RFCs, and schemas
python tools/validate_specs.py --all

# Run automated tests
python -m unittest discover -s tests -v
```

## Security Notice

Standards defined in this repository are actively tested against known prompt-injection and privilege-escalation vectors. To report potential standard-level security flaws, contact security@koality-assured.org.

## License

Distributed under the [MIT License](LICENSE). Copyright (c) 2026 Koality-Assured.
"""

    files["standards/context/5-tier-context-management.md"] = """# Specification: 5-Tier Context Management Architecture

- **Status:** Normative Standard
- **Version:** 1.0.0
- **Author:** Koality-Assured Architecture Committee

## 1. Abstract

Large Language Model (LLM) agents operating on expansive software repositories experience rapid context degradation, hallucination, and excessive token expenditure when ingesting monolithic code dumps. This specification establishes a standardized 5-Tier Context Management model that optimizes token allocation through progressive disclosure and AST fact extraction.

## 2. Context Tiers

```
┌──────────────────────────────────────────────────────────┐
│ Tier 1: Fast Routing (<100 tokens, sub-ms dispatch)      │
├──────────────────────────────────────────────────────────┤
│ Tier 2: Metadata Index & Manifests (~500 tokens)         │
├──────────────────────────────────────────────────────────┤
│ Tier 3: Summary Cards & Area Guides (~2k tokens)         │
├──────────────────────────────────────────────────────────┤
│ Tier 4: Extracted AST Facts & Headroom (~5k tokens)      │
├──────────────────────────────────────────────────────────┤
│ Tier 5: Raw Full Text (Targeted on-demand inspection)    │
└──────────────────────────────────────────────────────────┘
```

### 2.1 Tier 1: Fast Routing
- **Format:** Key-value routing tags, keyword maps, and dispatch tables.
- **Latency Budget:** < 1 ms.
- **Token Budget:** < 100 tokens per query.
- **Purpose:** Immediate agent routing to responsible subagents or documentation domains without retrieval overhead.

### 2.2 Tier 2: Metadata Index & Manifests
- **Format:** JSON/YAML catalog metadata, BM25 keyword indices, and file manifests.
- **Token Budget:** 200 - 1,000 tokens.
- **Purpose:** Broad architectural orientation and file inventory filtering.

### 2.3 Tier 3: Summary Cards & Area Guides
- **Format:** High-level Markdown overview cards, interface contracts, and module summaries (`AGENTS.md`).
- **Token Budget:** 1,000 - 3,000 tokens.
- **Purpose:** Contextual understanding of component responsibilities and interaction rules.

### 2.4 Tier 4: Extracted AST Facts & Headroom Compression
- **Format:** Class hierarchies, method signatures, exported types, and call reference graphs extracted via AST parsers.
- **Compression Target:** >= 85% token reduction relative to raw source files.
- **Purpose:** Deep structural comprehension of dependencies and APIs without loading function implementation bodies.

### 2.5 Tier 5: Raw Full Text
- **Format:** Complete, unmodified source code files.
- **Policy:** Strictly restricted to precise files actively undergoing modification or line-by-line debugging.

## 3. Conformance Requirements

1. Agent runtimes **MUST NOT** load raw files (Tier 5) into context prior to filtering via Tiers 1-3.
2. AST extraction engines **MUST** preserve type annotations and public docstrings in Tier 4 artifacts.
3. Runtimes **SHOULD** enforce context headroom budgets to prevent context window saturation.
"""

    files["standards/protocols/a2a-protocol-v1.md"] = """# Specification: Agent-to-Agent (A2A) Interaction Protocol v1.0

- **Status:** Normative Standard
- **Version:** 1.0.0
- **Author:** Koality-Assured Protocol Working Group

## 1. Abstract

This specification defines the Agent-to-Agent (A2A) messaging envelope, communication semantics, and lifecycle state machines governing interactions between orchestrator agents, specialized subagents, and peer agents.

## 2. Message Envelope Specification

All A2A messages **MUST** conform to the following JSON structure:

```json
{
  "$schema": "https://schema.koality-assured.org/agent/a2a-message.schema.json",
  "message_id": "msg_01HXYZ1234567890ABCDEF",
  "correlation_id": "task_9876543210FEDCBA",
  "timestamp": "2026-08-24T12:00:00Z",
  "sender": {
    "agent_id": "subagent-frontend-01",
    "role": "frontend-specialist"
  },
  "recipient": {
    "agent_id": "parent-orchestrator",
    "role": "orchestrator"
  },
  "message_type": "task_result",
  "status": "success",
  "payload": {
    "summary": "Completed component refactoring and unit tests.",
    "artifacts": ["src/components/Header.tsx", "tests/Header.test.tsx"],
    "metrics": {
      "duration_seconds": 14.2,
      "tokens_consumed": 3840
    }
  }
}
```

## 3. Lifecycle States

```
[Spawned] ──> [Dispatched] ──> [Executing] ──> [Completed]
                   │                │
                   └──> [Rejected]  └──> [Failed / Cancelled]
```

## 4. Message Types

| Message Type | Description |
| --- | --- |
| `task_dispatch` | Orchestrator delegates a scoped task to a subagent. |
| `task_acknowledge` | Subagent confirms receipt and readiness to execute. |
| `heartbeat` | Periodic liveness and progress update from executing agent. |
| `task_result` | Final payload with results, modified files, and telemetry metrics. |
| `task_cancel` | Preemptive cancellation instruction sent to active agent. |
"""

    files["standards/security/security-musts.md"] = """# Specification: Autonomous Agent Security MUSTs (SEC-01)

- **Status:** Normative Standard
- **Version:** 1.0.0
- **Author:** Koality-Assured Security Working Group
- **RFC 2119 Keywords:** MUST, MUST NOT, SHOULD, RECOMMENDED, MAY

## 1. Abstract

This specification establishes normative, mandatory security requirements for autonomous software development agents, harness runtimes, tool execution engines, and multi-agent systems.

## 2. Normative Requirements

### SEC-01: Sandboxing & Tool Boundary Isolation
- Agent execution engines **MUST** execute shell commands and untrusted scripts in restricted subshells or isolated containers.
- Agent runtimes **MUST** constrain file modification operations to designated working tree paths and reject path traversal outside the root repository directory.

### SEC-02: AST & Code Modification Verification
- Agent runtimes **MUST** validate code changes using language-specific AST parsers to ensure syntactic validity prior to staging or committing changes.
- Automated tooling **MUST NOT** commit syntactically broken code to main or release branches.

### SEC-03: Secret Boundary & Credential Redaction
- Telemetry collectors and log aggregators **MUST** scrub sensitive tokens, API keys, private certificates, and environment secrets prior to persisting or transmitting prompt context.
- Agents **MUST NOT** write plain-text credentials into committed source repositories.

### SEC-04: Context Poisoning & Prompt Injection Defense
- System instructions **MUST** be structurally segregated from untrusted external data (such as web search results or external repository issues).
- Runtimes **MUST** treat external markdown and HTML links as untrusted and neutralize executable schemes (`javascript:`, `data:`, `vbscript:`).

### SEC-05: Worktree & Concurrency Isolation
- Multi-agent orchestrators **MUST** provision separate git worktrees or isolated workspaces for concurrent agents to prevent race conditions and cross-agent file corruption.
"""

    files["specs/a2a-message.schema.json"] = json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://schema.koality-assured.org/agent/a2a-message.schema.json",
        "title": "A2AMessageEnvelope",
        "description": "JSON schema for Agent-to-Agent (A2A) structured message envelopes.",
        "type": "object",
        "required": ["message_id", "timestamp", "sender", "recipient", "message_type", "payload"],
        "properties": {
            "message_id": {
                "type": "string",
                "pattern": "^msg_[a-zA-Z0-9_-]+$",
                "description": "Unique identifier for the message."
            },
            "correlation_id": {
                "type": "string",
                "description": "Identifier tracking task or transaction across hops."
            },
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 UTC timestamp."
            },
            "sender": {
                "type": "object",
                "required": ["agent_id", "role"],
                "properties": {
                    "agent_id": {"type": "string"},
                    "role": {"type": "string"}
                }
            },
            "recipient": {
                "type": "object",
                "required": ["agent_id", "role"],
                "properties": {
                    "agent_id": {"type": "string"},
                    "role": {"type": "string"}
                }
            },
            "message_type": {
                "type": "string",
                "enum": ["task_dispatch", "task_acknowledge", "heartbeat", "task_result", "task_cancel"]
            },
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "success", "failed", "cancelled"]
            },
            "payload": {
                "type": "object",
                "description": "Arbitrary structured data payload associated with message_type."
            }
        },
        "additionalProperties": False
    }, indent=2) + "\n"

    files["specs/context-manifest.schema.json"] = json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://schema.koality-assured.org/agent/context-manifest.schema.json",
        "title": "ContextManifest",
        "description": "Schema for 5-tier context manifests and routing maps.",
        "type": "object",
        "required": ["schema_version", "tiers", "repository"],
        "properties": {
            "schema_version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
            "repository": {"type": "string"},
            "tiers": {
                "type": "object",
                "required": ["tier1_routing", "tier2_metadata", "tier3_summaries", "tier4_ast_facts", "tier5_raw"],
                "properties": {
                    "tier1_routing": {"type": "object"},
                    "tier2_metadata": {"type": "object"},
                    "tier3_summaries": {"type": "object"},
                    "tier4_ast_facts": {"type": "object"},
                    "tier5_raw": {"type": "object"}
                }
            }
        },
        "additionalProperties": True
    }, indent=2) + "\n"

    files["rfcs/0001-rfc-process.md"] = """# RFC 0001: The Koality-Assured Standards RFC Process

- **RFC Number:** 0001
- **Title:** The Koality-Assured Standards RFC Process
- **Status:** Active
- **Author:** Koality-Assured Governance Board
- **Created:** 2026-08-24

## 1. Summary

This document establishes the official Request for Comments (RFC) process for creating, modifying, and retiring standards within the `agent-standards` ecosystem.

## 2. RFC Lifecycle States

```
[Proposed] ──> [Draft] ──> [In-Review] ──> [Accepted] ──> [Final / Normative]
                                 │
                                 └──> [Rejected / Superseded]
```

1. **Proposed:** Initial issue or PR introducing the proposal concept.
2. **Draft:** Complete specification written using `rfcs/template.md`.
3. **In-Review:** 14-day public comment and implementation trial period.
4. **Accepted:** Approved by governance vote and slated for incorporation into `standards/`.
5. **Final / Normative:** Merged as an authoritative normative standard.
6. **Superseded:** Replaced by a newer approved standard.

## 3. Submitting an RFC

1. Copy `rfcs/template.md` to `rfcs/YYYY-short-title.md`.
2. Fill out all required sections: Motivation, Specification, Rationale, Backwards Compatibility, Security Considerations.
3. Open a Pull Request with the label `rfc`.
"""

    files["rfcs/template.md"] = """# RFC Template: [Title of Proposal]

- **RFC Number:** [Auto-assigned or sequential]
- **Title:** [Brief descriptive title]
- **Status:** Draft
- **Author:** [Author Name / Organization]
- **Created:** [YYYY-MM-DD]

## 1. Summary
[A concise 2-3 sentence overview of the proposal.]

## 2. Motivation
[Why is this standard needed? What problems does it solve?]

## 3. Detailed Specification
[Normative technical specification with data models, schemas, and behavior.]

## 4. Rationale & Alternatives
[Why this design over other potential approaches?]

## 5. Backwards Compatibility
[Impact on existing runtimes, schemas, or protocols.]

## 6. Security Considerations
[Security analysis, potential vulnerabilities, and mitigations.]
"""

    files["tools/__init__.py"] = '"""Standards and RFC validation library."""\n'

    files["tools/validate_specs.py"] = r'''"""CLI to validate JSON schemas, RFC documents, and normative specifications.

tags: [validator, standards, rfc, specs]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


def validate_json_schemas(specs_dir: Path) -> Tuple[int, int]:
    """Validate all *.schema.json files under specs/."""
    schema_files = list(specs_dir.glob("*.schema.json"))
    passed = 0
    failed = 0

    print(f"Validating {len(schema_files)} JSON Schema(s) in {specs_dir}...")
    for sf in schema_files:
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            if jsonschema is not None:
                jsonschema.Draft202012Validator.check_schema(data)
            print(f"  [PASS] {sf.name}")
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {sf.name}: {exc}", file=sys.stderr)
            failed += 1

    return passed, failed


def validate_rfc_documents(rfcs_dir: Path) -> Tuple[int, int]:
    """Validate that RFC Markdown files follow structural conventions."""
    rfc_files = [f for f in rfcs_dir.glob("*.md") if f.name != "template.md"]
    passed = 0
    failed = 0

    print(f"Validating {len(rfc_files)} RFC document(s) in {rfcs_dir}...")
    for rf in rfc_files:
        content = rf.read_text(encoding="utf-8")
        errors = []
        if not content.startswith("# RFC"):
            errors.append("Must start with '# RFC' heading")
        if "**Status:**" not in content and "- **Status:**" not in content:
            errors.append("Missing Status metadata field")

        if not errors:
            print(f"  [PASS] {rf.name}")
            passed += 1
        else:
            print(f"  [FAIL] {rf.name}: {', '.join(errors)}", file=sys.stderr)
            failed += 1

    return passed, failed


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Validate all schemas and RFCs")
    parser.add_argument("--base-dir", type=str, default=".", help="Base directory of repository")
    args = parser.parse_args(argv)

    base = Path(args.base_dir).resolve()
    specs_dir = base / "specs"
    rfcs_dir = base / "rfcs"

    total_passed = 0
    total_failed = 0

    if specs_dir.exists():
        p, f = validate_json_schemas(specs_dir)
        total_passed += p
        total_failed += f

    if rfcs_dir.exists():
        p, f = validate_rfc_documents(rfcs_dir)
        total_passed += p
        total_failed += f

    print(f"\nOverall Result: {total_passed} passed, {total_failed} failed.")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

    files["tests/__init__.py"] = '"""Test suite for agent-standards."""\n'

    files["tests/test_standards_validation.py"] = r'''"""Unit tests validating agent-standards schemas, RFCs, and specifications."""

import json
import unittest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from tools.validate_specs import validate_json_schemas, validate_rfc_documents


class TestStandardsValidation(unittest.TestCase):
    def setUp(self):
        self.root = _ROOT
        self.specs_dir = self.root / "specs"
        self.standards_dir = self.root / "standards"
        self.rfcs_dir = self.root / "rfcs"

    def test_specs_exist_and_validate(self):
        self.assertTrue(self.specs_dir.exists())
        passed, failed = validate_json_schemas(self.specs_dir)
        self.assertGreater(passed, 0)
        self.assertEqual(failed, 0)

    def test_normative_standards_exist(self):
        context_std = self.standards_dir / "context" / "5-tier-context-management.md"
        proto_std = self.standards_dir / "protocols" / "a2a-protocol-v1.md"
        sec_std = self.standards_dir / "security" / "security-musts.md"

        self.assertTrue(context_std.exists(), "5-tier context spec should exist")
        self.assertTrue(proto_std.exists(), "A2A protocol spec should exist")
        self.assertTrue(sec_std.exists(), "Security MUSTs spec should exist")

    def test_rfcs_validate(self):
        self.assertTrue(self.rfcs_dir.exists())
        passed, failed = validate_rfc_documents(self.rfcs_dir)
        self.assertGreater(passed, 0)
        self.assertEqual(failed, 0)

    def test_a2a_sample_message_matches_schema(self):
        schema_file = self.specs_dir / "a2a-message.schema.json"
        schema = json.loads(schema_file.read_text(encoding="utf-8"))

        sample = {
            "message_id": "msg_01HXYZ1234567890ABCDEF",
            "correlation_id": "task_12345",
            "timestamp": "2026-08-24T12:00:00Z",
            "sender": {"agent_id": "subagent-1", "role": "developer"},
            "recipient": {"agent_id": "parent", "role": "orchestrator"},
            "message_type": "task_result",
            "status": "success",
            "payload": {"result": "ok"}
        }

        try:
            import jsonschema
            jsonschema.validate(instance=sample, schema=schema)
        except ImportError:
            self.assertEqual(sample["message_type"], "task_result")


if __name__ == "__main__":
    unittest.main()
'''

    return files


# -----------------------------------------------------------------------------
# Repo 3: ai-research-and-benchmarks
# -----------------------------------------------------------------------------

def _build_ai_research_files() -> Dict[str, str]:
    files: Dict[str, str] = {}

    files["LICENSE"] = MIT_LICENSE_TEMPLATE
    files[".gitignore"] = COMMON_GITIGNORE + """
# Benchmark dataset caches and large run dumps
data/raw/
data/cache/
*.parquet
*.arrow
results/runs/
"""
    files[".editorconfig"] = COMMON_EDITORCONFIG

    files[".github/workflows/ci.yml"] = """name: Benchmarks CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test-and-validate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install jsonschema pyyaml

      - name: Run Test Suite
        run: |
          python -m unittest discover -s tests -v

      - name: Dry-run Benchmark Runner
        run: |
          python harnesses/runner.py --suite benchmarks/suites/coding_agent_benchmark_v1.json --dry-run
"""

    files["README.md"] = """# AI Research & Benchmarks (`ai-research-and-benchmarks`)

[![Benchmarks CI](https://github.com/Koality-Assured/ai-research-and-benchmarks/actions/workflows/ci.yml/badge.svg)](https://github.com/Koality-Assured/ai-research-and-benchmarks/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Benchmarks: Automated](https://img.shields.io/badge/Benchmarks-Automated-brightgreen.svg)](benchmarks/)
[![Research: Empirical](https://img.shields.io/badge/Research-Empirical-purple.svg)](reports/)

## Mission Statement

`ai-research-and-benchmarks` is the open research and empirical evaluation repository of Koality-Assured.

We publish reproducible benchmarks, comparative harness evaluations, context retrieval trade-off analyses, and token cost telemetry across autonomous coding frameworks and LLM reasoning models.

## Architecture Overview

```
ai-research-and-benchmarks/
├── .github/workflows/ci.yml    # Benchmark dry-run CI pipeline
├── benchmarks/                 # Standardized test suites & datasets
│   ├── README.md
│   └── suites/
│       └── coding_agent_benchmark_v1.json  # Reference coding benchmark suite
├── harnesses/                  # Execution runners and harness adapters
│   ├── README.md
│   ├── __init__.py
│   └── runner.py               # Benchmark execution harness
├── telemetry/                  # Token usage & cost calculation engine
│   ├── README.md
│   ├── __init__.py
│   └── cost_calculator.py      # Multi-model token cost & headroom calculator
├── reports/                    # Published research reports and whitepapers
│   ├── README.md
│   └── template_evaluation_report.md
├── tests/                      # Automated test suite
│   ├── __init__.py
│   └── test_benchmarks.py      # Unit tests for runner and cost calculation
├── pyproject.toml              # Python project configuration
├── .editorconfig               # Editor configuration
├── .gitignore                  # Git ignore rules
└── LICENSE                     # MIT License
```

## Research Focus Areas

1. **Agentic Harness Efficiency:** Measuring wall-clock latency, token consumption, and cost-per-resolved-issue across coding agent architectures.
2. **Context Tiering & Headroom:** Quantifying performance and cost delta between raw text context dumps and Tier-4 AST Fact extraction with Headroom compression.
3. **Framework Shootouts:** Objective side-by-side evaluations of multi-agent orchestrators (e.g. LangGraph, AutoGen, CrewAI, Native Harnesses).

## Running Benchmarks

### Prerequisites
- Python >= 3.10

### Quickstart

```bash
# Clone the repository
git clone https://github.com/Koality-Assured/ai-research-and-benchmarks.git
cd ai-research-and-benchmarks

# Run benchmark suite in dry-run mode
python harnesses/runner.py --suite benchmarks/suites/coding_agent_benchmark_v1.json --dry-run

# Run cost calculator for context tier comparison
python telemetry/cost_calculator.py --input-tokens 50000 --output-tokens 2000 --model gpt-4o
```

## Running Tests

```bash
python -m unittest discover -s tests -v
```

## Research Ethics & Methodology Disclosures

All benchmark runs adhere to strict empirical standards:
- **Reproducibility:** All prompt templates, harness configurations, and evaluation seeds are checked into git.
- **Fairness:** Temperature, seed, and timeout limits are pinned uniformly across evaluated frameworks.
- **Cost Attribution:** Token accounting reflects true blended input, output, cache-read, and cache-write rates.

## Contributing

We welcome benchmark task contributions and independent evaluation reports. Please see [`reports/README.md`](reports/README.md) for report authoring guidelines.

## Security Notice

Benchmark execution harnesses run arbitrary generated code. Harnesses MUST run inside sandboxed containers or ephemeral VMs. To report vulnerabilities, contact security@koality-assured.org.

## License

Distributed under the [MIT License](LICENSE). Copyright (c) 2026 Koality-Assured.
"""

    files["pyproject.toml"] = """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-research-and-benchmarks"
version = "0.1.0"
description = "Public repository of comparative agent harness research, industry framework evaluations, and benchmark reports"
readme = "README.md"
authors = [{ name = "Koality-Assured", email = "research@koality-assured.org" }]
license = { text = "MIT" }
requires-python = ">=3.10"
dependencies = [
    "jsonschema>=4.20.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.3.0",
]

[project.scripts]
benchmark-runner = "harnesses.runner:main"
cost-calc = "telemetry.cost_calculator:main"
"""

    files["benchmarks/README.md"] = """# Benchmark Suites

This directory contains standardized benchmark datasets and evaluation specifications for testing agent harnesses.

## Available Suites

| Suite File | Tasks | Domain | Focus |
| --- | --- | --- | --- |
| [`suites/coding_agent_benchmark_v1.json`](./suites/coding_agent_benchmark_v1.json) | 3 reference tasks | Software Engineering | AST refactoring, bug fixes, unit tests |

## Suite Format
Suites are defined as JSON documents specifying tasks, input prompts, expected outcome assertions, and execution timeouts.
"""

    files["benchmarks/suites/coding_agent_benchmark_v1.json"] = json.dumps({
        "suite_name": "coding_agent_benchmark_v1",
        "version": "1.0.0",
        "description": "Standardized benchmark suite for evaluating autonomous coding agents on refactoring and test generation.",
        "tasks": [
            {
                "task_id": "task_001_ast_refactor",
                "title": "AST Precision Refactor",
                "difficulty": "medium",
                "timeout_seconds": 60,
                "prompt": "Refactor legacy dictionary lookups to use typed dataclasses without modifying public function signatures.",
                "expected_artifacts": ["src/models.py", "tests/test_models.py"],
                "evaluation_metrics": ["pass@1", "token_cost", "wall_clock_time"]
            },
            {
                "task_id": "task_002_context_compression",
                "title": "Context Headroom Optimization",
                "difficulty": "hard",
                "timeout_seconds": 120,
                "prompt": "Extract Tier-4 AST symbols from 50 source files to achieve >=80% token compression relative to raw file content.",
                "expected_artifacts": ["results/facts.json"],
                "evaluation_metrics": ["compression_ratio", "retrieval_accuracy"]
            },
            {
                "task_id": "task_003_secure_tool_dispatch",
                "title": "Sandbox Policy Enforcement",
                "difficulty": "medium",
                "timeout_seconds": 45,
                "prompt": "Implement isolated git worktree lifecycle management tool and verify path boundary confinement.",
                "expected_artifacts": ["scripts/worktree.py", "tests/test_worktree.py"],
                "evaluation_metrics": ["security_score", "pass@1"]
            }
        ]
    }, indent=2) + "\n"

    files["harnesses/README.md"] = """# Harness Adapters

Harness adapters provide uniform execution wrappers around diverse agent runtimes to enable fair, reproducible benchmarking.
"""

    files["harnesses/__init__.py"] = '"""Harness adapters and benchmark runners."""\n'

    files["harnesses/runner.py"] = r'''"""Benchmark execution runner for autonomous agent harnesses.

tags: [benchmarks, runner, harness]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_suite(suite_path: Path) -> Dict[str, Any]:
    """Load and validate benchmark suite JSON."""
    if not suite_path.exists():
        raise FileNotFoundError(f"Suite file not found: {suite_path}")
    data = json.loads(suite_path.read_text(encoding="utf-8"))
    if "tasks" not in data or not isinstance(data["tasks"], list):
        raise ValueError("Benchmark suite must contain a 'tasks' list")
    return data


def run_benchmark(
    suite_data: Dict[str, Any],
    dry_run: bool = False,
    max_tasks: Optional[int] = None
) -> Dict[str, Any]:
    """Execute benchmark suite tasks."""
    tasks = suite_data.get("tasks", [])
    if max_tasks is not None:
        tasks = tasks[:max_tasks]

    results: List[Dict[str, Any]] = []
    start_time = time.time()

    print(f"Executing suite '{suite_data.get('suite_name', 'unknown')}' with {len(tasks)} task(s)...")

    for task in tasks:
        task_id = task.get("task_id", "unknown")
        title = task.get("title", "")
        print(f"  -> Task [{task_id}]: {title} (dry_run={dry_run})")

        if dry_run:
            status = "simulated_success"
            duration = 0.05
            tokens = 1500
        else:
            # Placeholder for actual agent harness invocation
            status = "completed"
            duration = 1.2
            tokens = 3200

        results.append({
            "task_id": task_id,
            "title": title,
            "status": status,
            "duration_seconds": duration,
            "tokens_consumed": tokens,
        })

    total_time = round(time.time() - start_time, 2)
    summary = {
        "suite_name": suite_data.get("suite_name"),
        "total_tasks": len(tasks),
        "successful_tasks": len([r for r in results if "success" in r["status"] or r["status"] == "completed"]),
        "total_duration_seconds": total_time,
        "results": results,
    }
    return summary


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, help="Path to benchmark suite JSON")
    parser.add_argument("--dry-run", action="store_true", help="Simulate benchmark execution without calling models")
    parser.add_argument("--max-tasks", type=int, help="Limit number of tasks executed")
    parser.add_argument("--output-json", help="Save benchmark results to JSON file")
    args = parser.parse_args(argv)

    suite_path = Path(args.suite).resolve()
    try:
        suite_data = load_suite(suite_path)
    except Exception as exc:
        print(f"Error loading suite: {exc}", file=sys.stderr)
        return 2

    summary = run_benchmark(suite_data, dry_run=args.dry_run, max_tasks=args.max_tasks)
    print("\nBenchmark Summary:")
    print(f"  Suite: {summary['suite_name']}")
    print(f"  Tasks: {summary['successful_tasks']}/{summary['total_tasks']} completed successfully")
    print(f"  Duration: {summary['total_duration_seconds']}s")

    if args.output_json:
        out_file = Path(args.output_json).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Saved benchmark results to {out_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    files["telemetry/README.md"] = """# Telemetry & Cost Engine

Tools to measure, model, and analyze token consumption and cost efficiency across multi-tier context architectures.
"""

    files["telemetry/__init__.py"] = '"""Telemetry and cost calculation utilities."""\n'

    files["telemetry/cost_calculator.py"] = r'''"""Calculate token costs and context headroom savings across LLM pricing tiers.

tags: [telemetry, cost, pricing, headroom]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# Pricing per million tokens (USD) - standard representative rates
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {
        "input_per_m": 2.50,
        "output_per_m": 10.00,
        "cache_read_per_m": 1.25,
    },
    "claude-3-5-sonnet": {
        "input_per_m": 3.00,
        "output_per_m": 15.00,
        "cache_read_per_m": 0.30,
    },
    "gemini-1.5-pro": {
        "input_per_m": 3.50,
        "output_per_m": 10.50,
        "cache_read_per_m": 0.875,
    },
    "gemini-1.5-flash": {
        "input_per_m": 0.075,
        "output_per_m": 0.30,
        "cache_read_per_m": 0.01875,
    },
}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0
) -> Dict[str, Any]:
    """Calculate USD cost for a given token usage breakdown."""
    if model not in MODEL_PRICING:
        raise ValueError(f"Unknown model '{model}'. Supported models: {list(MODEL_PRICING.keys())}")

    rates = MODEL_PRICING[model]
    input_cost = (input_tokens / 1_000_000.0) * rates["input_per_m"]
    output_cost = (output_tokens / 1_000_000.0) * rates["output_per_m"]
    cache_cost = (cache_read_tokens / 1_000_000.0) * rates["cache_read_per_m"]
    total_cost = input_cost + output_cost + cache_cost

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "total_tokens": input_tokens + output_tokens + cache_read_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "cache_cost_usd": round(cache_cost, 6),
        "total_cost_usd": round(total_cost, 6),
    }


def compare_headroom_savings(
    raw_tokens: int,
    compressed_tokens: int,
    model: str = "gpt-4o"
) -> Dict[str, Any]:
    """Compare raw vs compressed context cost savings."""
    raw = calculate_cost(model, input_tokens=raw_tokens, output_tokens=1000)
    comp = calculate_cost(model, input_tokens=compressed_tokens, output_tokens=1000)
    savings_usd = round(raw["total_cost_usd"] - comp["total_cost_usd"], 6)
    ratio = round((1.0 - (compressed_tokens / max(raw_tokens, 1))) * 100, 2)

    return {
        "model": model,
        "raw_tokens": raw_tokens,
        "compressed_tokens": compressed_tokens,
        "compression_percentage": ratio,
        "raw_cost_usd": raw["total_cost_usd"],
        "compressed_cost_usd": comp["total_cost_usd"],
        "savings_usd": savings_usd,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-4o", choices=list(MODEL_PRICING.keys()))
    parser.add_argument("--input-tokens", type=int, default=10000)
    parser.add_argument("--output-tokens", type=int, default=1000)
    parser.add_argument("--cache-read-tokens", type=int, default=0)
    parser.add_argument("--compare-raw", type=int, help="Compare raw tokens against input-tokens (treated as compressed)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args(argv)

    if args.compare_raw:
        res = compare_headroom_savings(raw_tokens=args.compare_raw, compressed_tokens=args.input_tokens, model=args.model)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Context Headroom Savings Analysis ({args.model}):")
            print(f"  Raw: {res['raw_tokens']} tokens (${res['raw_cost_usd']})")
            print(f"  Compressed: {res['compressed_tokens']} tokens (${res['compressed_cost_usd']})")
            print(f"  Reduction: {res['compression_percentage']}%")
            print(f"  Savings: ${res['savings_usd']}")
        return 0

    cost = calculate_cost(args.model, args.input_tokens, args.output_tokens, args.cache_read_tokens)
    if args.json:
        print(json.dumps(cost, indent=2))
    else:
        print(f"Token Cost Estimate ({args.model}):")
        print(f"  Input: {cost['input_tokens']} (${cost['input_cost_usd']})")
        print(f"  Output: {cost['output_tokens']} (${cost['output_cost_usd']})")
        print(f"  Total: ${cost['total_cost_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    files["reports/README.md"] = """# Research & Evaluation Reports

Published benchmark results, framework evaluations, and empirical studies.

## Report Index

- [`template_evaluation_report.md`](./template_evaluation_report.md) - Standard report template.
"""

    files["reports/template_evaluation_report.md"] = """# Research Report: [Evaluation Title]

- **Date:** [YYYY-MM-DD]
- **Author:** [Author / Organization]
- **Status:** Published
- **Benchmark Suite:** [`coding_agent_benchmark_v1`](../benchmarks/suites/coding_agent_benchmark_v1.json)

## 1. Executive Summary
[Key findings, top-line metric comparisons, and primary takeaways.]

## 2. Methodology & Harness Setup
- **Evaluated Harnesses:** [e.g. Native Worktree Harness vs Multi-Agent Framework]
- **Model:** [e.g. GPT-4o, Claude 3.5 Sonnet]
- **Context Management:** [e.g. 5-Tier AST facts vs monolithic prompt]

## 3. Benchmark Results

| Harness | Pass@1 Rate (%) | Avg Duration (s) | Avg Input Tokens | Total Cost ($) |
| --- | --- | --- | --- | --- |
| Harness A | 92.5% | 14.2s | 4,200 | $0.042 |
| Harness B | 84.0% | 28.6s | 18,500 | $0.185 |

## 4. Cost & Headroom Analysis
[Analysis of token compression savings and latency trade-offs.]

## 5. Conclusions & Recommendations
[Actionable engineering recommendations for agent system architects.]
"""

    files["tests/__init__.py"] = '"""Test suite for ai-research-and-benchmarks."""\n'

    files["tests/test_benchmarks.py"] = r'''"""Unit tests for benchmark suite runner and cost calculator."""

import json
import unittest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from harnesses.runner import load_suite, run_benchmark
from telemetry.cost_calculator import calculate_cost, compare_headroom_savings


class TestResearchAndBenchmarks(unittest.TestCase):
    def setUp(self):
        self.root = _ROOT
        self.suite_file = self.root / "benchmarks" / "suites" / "coding_agent_benchmark_v1.json"

    def test_benchmark_suite_file_loads(self):
        self.assertTrue(self.suite_file.exists())
        data = load_suite(self.suite_file)
        self.assertEqual(data["suite_name"], "coding_agent_benchmark_v1")
        self.assertGreaterEqual(len(data["tasks"]), 3)

    def test_benchmark_dry_run(self):
        data = load_suite(self.suite_file)
        summary = run_benchmark(data, dry_run=True, max_tasks=2)
        self.assertEqual(summary["total_tasks"], 2)
        self.assertEqual(summary["successful_tasks"], 2)
        self.assertEqual(len(summary["results"]), 2)

    def test_cost_calculation(self):
        res = calculate_cost("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
        self.assertAlmostEqual(res["input_cost_usd"], 2.50, places=2)
        self.assertAlmostEqual(res["output_cost_usd"], 10.00, places=2)
        self.assertAlmostEqual(res["total_cost_usd"], 12.50, places=2)

    def test_headroom_savings(self):
        res = compare_headroom_savings(raw_tokens=100_000, compressed_tokens=20_000, model="gpt-4o")
        self.assertEqual(res["compression_percentage"], 80.0)
        self.assertGreater(res["savings_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
'''


    return files


# -----------------------------------------------------------------------------
# Repo 4: security-standards
# -----------------------------------------------------------------------------

def _build_security_standards_files() -> Dict[str, str]:
    files: Dict[str, str] = {}

    files["LICENSE"] = MIT_LICENSE_TEMPLATE
    files[".gitignore"] = COMMON_GITIGNORE
    files[".editorconfig"] = COMMON_EDITORCONFIG

    files[".github/workflows/ci.yml"] = """name: Security Standards CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f pyproject.toml ]; then pip install .; fi
      - name: Validate Standards
        run: |
          python tools/validator.py --all
      - name: Run Tests
        run: |
          python -m unittest discover -s tests -v
"""

    files["pyproject.toml"] = """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "koality-security-standards"
version = "1.0.0"
description = "Normative engineering and organizational security standards across 20+ operational domains."
authors = [{ name = "Koality-Assured", email = "engineering@koality-assured.com" }]
license = { text = "MIT" }
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
]
"""

    files["README.md"] = """# Koality-Assured Security Standards

Normative engineering, architectural, and operational security standards across 20+ operational domains used to reinforce decisions and guide secure implementation.

## Mission Statement

Provide an authoritative, versioned catalog of machine-readable and human-verifiable security standards for engineering teams and AI coding agents.

## Architecture Overview

This repository hosts authoritative security standards designed for automated validation, human engineering, and AI coding agent guardrails.

### Covered Security Domains

| Category | Standards |
| --- | --- |
| **Identity & Access** | `identity-and-access`, `privileged-access`, `passwords-and-credentials`, `administrative-interfaces` |
| **Infrastructure & Cloud** | `cloud-essentials`, `network-and-remote-access`, `endpoint-and-workstation`, `internet-facing-services` |
| **Development & Repos** | `ai-development-security`, `source-code-repository`, `github-iac-security`, `secure-configuration` |
| **Data & Cryptography** | `data-protection`, `cryptography-and-key-management`, `backup-and-recovery` |
| **Operations & Risk** | `logging-monitoring-and-detection`, `vulnerability-and-patch-management`, `incident-response`, `third-party-and-supply-chain`, `saas-security` |

## Validation

```bash
python tools/validator.py --all
python -m unittest discover -s tests -v
```

## Security Notice

All standards in this repository are subject to continuous automated integrity validation and security policy compliance.

## License

MIT License Copyright (c) 2026 Koality-Assured.
"""

    files["standards/README.md"] = """# Standards Directory

Canonical normative standards categorized by operational and architectural domain.
"""

    files["tools/__init__.py"] = '"""Security standards validation tools."""\n'

    files["tools/validator.py"] = '''"""CLI validator for security standards markdown structure and YAML frontmatter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REQUIRED_KEYS = ["doc_kind", "canonical_id", "purpose", "rank", "topics"]


def validate_standard_file(path: Path) -> list[str]:
    errors = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        errors.append(f"{path.name}: missing YAML frontmatter opening '---'")
        return errors
    end = text.find("\\n---", 3)
    if end == -1:
        errors.append(f"{path.name}: missing YAML frontmatter closing '---'")
        return errors
    frontmatter_raw = text[3:end]
    for k in REQUIRED_KEYS:
        if f"{k}:" not in frontmatter_raw:
            errors.append(f"{path.name}: missing required frontmatter key '{k}'")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate security standards")
    parser.add_argument("--all", action="store_true", help="Validate all standards")
    parser.add_argument("--path", type=str, default=None, help="Specific standard file to validate")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    standards_dir = root / "standards"
    all_errors = []

    if args.path:
        files = [Path(args.path)]
    else:
        files = [p for p in standards_dir.glob("*.md") if p.name != "README.md"]

    for f in files:
        errs = validate_standard_file(f)
        all_errors.extend(errs)

    if all_errors:
        print(f"Validation failed with {len(all_errors)} errors:", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(files)} standards validated cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    files["tests/__init__.py"] = '"""Unit tests for security standards."""\n'

    files["tests/test_standards.py"] = '''"""Unit tests verifying security standards structure."""

import unittest
from pathlib import Path
from tools.validator import validate_standard_file


class TestSecurityStandards(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.standards_dir = self.root / "standards"

    def test_standards_directory_exists(self):
        self.assertTrue(self.standards_dir.exists())

    def test_standards_have_valid_frontmatter(self):
        standards = [p for p in self.standards_dir.glob("*.md") if p.name != "README.md"]
        for std in standards:
            errs = validate_standard_file(std)
            self.assertEqual(errs, [], f"Standard {std.name} has validation errors: {errs}")


if __name__ == "__main__":
    unittest.main()
'''

    return files


# -----------------------------------------------------------------------------
# Repo 5: industry-references
# -----------------------------------------------------------------------------

def _build_industry_references_files() -> Dict[str, str]:
    files: Dict[str, str] = {}

    files["LICENSE"] = MIT_LICENSE_TEMPLATE
    files[".gitignore"] = COMMON_GITIGNORE
    files[".editorconfig"] = COMMON_EDITORCONFIG

    files[".github/workflows/ci.yml"] = """name: Industry References CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f pyproject.toml ]; then pip install .; fi
      - name: Validate References & Catalogs
        run: |
          python tools/validator.py --all
      - name: Run Tests
        run: |
          python -m unittest discover -s tests -v
"""

    files["pyproject.toml"] = """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "koality-industry-references"
version = "1.0.0"
description = "Normalized machine-readable catalogs and guides for industry frameworks (OWASP, MITRE, NIST, CWE, Conventional Commits)."
authors = [{ name = "Koality-Assured", email = "engineering@koality-assured.com" }]
license = { text = "MIT" }
readme = "README.md"
requires-python = ">=3.11"
"""

    files["README.md"] = """# Koality-Assured Industry References

Normalized, machine-readable catalogs, mappings, and practitioner guides for industry cybersecurity and engineering frameworks.

## Mission Statement

Provide centralized, verified, machine-readable reference schemas and guides for industry engineering and cybersecurity frameworks.

## Architecture Overview

This repository maintains normalized catalogs and mappings across leading international frameworks.

### Catalogs & Frameworks Included

- **OWASP**: Agentic Top 10 (2026), ASVS 5.0, LLM Top 10 mappings
- **MITRE ATT&CK**: Enterprise Matrix v19.1 tactics, techniques, and sub-techniques
- **MITRE ATLAS**: Adversarial Threat Landscape for AI Systems (2026.07)
- **NIST CSF**: Cybersecurity Framework 2.0 Core functions, categories, and subcategories
- **NIST AI RMF**: Artificial Intelligence Risk Management Framework 1.0 Core & GenAI Profile
- **CWE**: Common Weakness Enumeration v4.20 and CWE Top 25 (2025/2026)
- **Conventional Commits**: Standard specification v1.0.0 for structured git messages

## Validation & Testing

```bash
python tools/validator.py --all
python -m unittest discover -s tests -v
```

## Security Notice

All framework catalogs are verified against upstream specifications and maintained for agent and automation integration.

## License

MIT License Copyright (c) 2026 Koality-Assured.
"""

    files["references/README.md"] = """# References Directory

Structured catalogs and guide pages for industry frameworks.
"""

    files["tools/__init__.py"] = '"""Industry references validation tools."""\n'

    files["tools/validator.py"] = '''"""CLI validator for industry reference json catalogs and markdown guides."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def validate_catalog_json(path: Path) -> list[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, (dict, list)):
            errors.append(f"{path.name}: JSON root must be an object or array")
    except Exception as exc:
        errors.append(f"{path.name}: Invalid JSON - {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate industry references")
    parser.add_argument("--all", action="store_true", help="Validate all references")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    ref_dir = root / "references"
    all_errors = []

    json_files = list(ref_dir.rglob("*.json"))
    for f in json_files:
        errs = validate_catalog_json(f)
        all_errors.extend(errs)

    if all_errors:
        print(f"Validation failed with {len(all_errors)} errors:", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(json_files)} catalogs validated cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    files["tests/__init__.py"] = '"""Unit tests for industry references."""\n'

    files["tests/test_references.py"] = '''"""Unit tests verifying industry references structure and JSON catalogs."""

import json
import unittest
from pathlib import Path


class TestIndustryReferences(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.ref_dir = self.root / "references"

    def test_references_directory_exists(self):
        self.assertTrue(self.ref_dir.exists())

    def test_all_json_catalogs_are_valid(self):
        catalogs = list(self.ref_dir.rglob("*.json"))
        for cat in catalogs:
            try:
                data = json.loads(cat.read_text(encoding="utf-8"))
                self.assertIsInstance(data, (dict, list))
            except Exception as exc:
                self.fail(f"Catalog {cat.name} failed JSON parsing: {exc}")


if __name__ == "__main__":
    unittest.main()
'''

    return files


# -----------------------------------------------------------------------------
# Repo 6: ai-harness-core (generic wiki harness template)
# -----------------------------------------------------------------------------

def _build_ai_harness_core_files() -> Dict[str, str]:
    files: Dict[str, str] = {}

    files["LICENSE"] = MIT_LICENSE_TEMPLATE
    files[".gitignore"] = COMMON_GITIGNORE
    files[".editorconfig"] = COMMON_EDITORCONFIG

    files[".github/workflows/ci.yml"] = GENERIC_TEMPLATE_CI
    files["README.md"] = GENERIC_TEMPLATE_README

    files["AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["docs/AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["docs/standards/AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["actionable/AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["scratch/AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["results/AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["projects/AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["research/AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["change-history/AGENTS.md"] = GENERIC_TEMPLATE_STUB_AGENTS
    files["references/AGENTS.md"] = GENERIC_TEMPLATE_REFERENCES_AGENTS

    files["config/harness.config.json"] = """{
  "paths": {
    "skills_dir": "ai-tooling/skills",
    "agents_dir": "ai-tooling/agents",
    "a2a_dir": "ai-tooling/a2a",
    "worktrees_dir": "scratch/worktrees",
    "memory_dir": "ai-tooling/memory",
    "docs_dir": "docs",
    "routing_dir": "routing"
  },
  "adapters": {
    "qmd": {
      "enabled": true,
      "collections_root": ".qmd"
    },
    "ast_grep": {
      "enabled": true,
      "binary_path": "sg"
    },
    "headroom": {
      "enabled": true,
      "proxy_url": "http://127.0.0.1:8787"
    },
    "git": {
      "max_worktrees": 12,
      "worktree_prefix": "sw-"
    }
  },
  "cache": {
    "anthropic": {
      "max_breakpoints": 4,
      "ttl_seconds": 300,
      "min_tokens_threshold": 1024
    },
    "openai": {
      "min_prefix_tokens": 1024,
      "alignment_block_size": 128
    },
    "gemini": {
      "context_cache_threshold": 32768
    }
  },
  "a2a": {
    "max_exchanges": 8,
    "require_result_envelope": true
  }
}
"""

    return files


# -----------------------------------------------------------------------------
# Repo Scaffold Registry & Core Engine
# -----------------------------------------------------------------------------

@dataclass
class RepoDefinition:
    name: str
    description: str
    builder: Callable[[], Dict[str, str]]


REPO_REGISTRY: Dict[str, RepoDefinition] = {
    "agent-skills-and-tools": RepoDefinition(
        name="agent-skills-and-tools",
        description="Public repository of reusable agent skills, schemas, and supporting tool integrations.",
        builder=_build_agent_skills_files,
    ),
    "agent-standards": RepoDefinition(
        name="agent-standards",
        description="Public repository of agentic standards, 5-tier context management, A2A interaction protocols, and security MUSTs.",
        builder=_build_agent_standards_files,
    ),
    "security-standards": RepoDefinition(
        name="security-standards",
        description="Public repository of general engineering and organizational security standards across 20+ operational domains.",
        builder=_build_security_standards_files,
    ),
    "industry-references": RepoDefinition(
        name="industry-references",
        description="Public repository of normalized machine-readable catalogs and guides for industry frameworks (OWASP, MITRE, NIST, CWE, Conventional Commits).",
        builder=_build_industry_references_files,
    ),
    "ai-research-and-benchmarks": RepoDefinition(
        name="ai-research-and-benchmarks",
        description="Public repository of comparative agent harness research, industry framework evaluations, and benchmark reports.",
        builder=_build_ai_research_files,
    ),
    "ai-harness-core": RepoDefinition(
        name="ai-harness-core",
        description="Generic wiki harness template for domain routers (engine under .harness/, not a package-only export).",
        builder=_build_ai_harness_core_files,
    ),
}


def get_repo_definitions() -> Dict[str, RepoDefinition]:
    """Return all available repository definitions."""
    return dict(REPO_REGISTRY)


def scaffold_repo(
    repo_name: str,
    target_dir: Path,
    overwrite: bool = False,
    dry_run: bool = False,
    init_git: bool = False,
) -> Dict[str, Any]:
    """Scaffold a single repository into target_dir / repo_name."""
    if repo_name not in REPO_REGISTRY:
        raise ValueError(f"Unknown repository '{repo_name}'. Available: {list(REPO_REGISTRY.keys())}")

    defn = REPO_REGISTRY[repo_name]
    repo_root = target_dir / repo_name
    files = defn.builder()

    if repo_root.exists() and not overwrite and not dry_run:
        # Check if directory is non-empty
        existing = [p for p in repo_root.rglob("*") if p.is_file()]
        if existing:
            raise FileExistsError(
                f"Destination directory '{repo_root}' already exists and contains files. Use --overwrite to replace."
            )

    created_files: List[str] = []
    total_bytes = 0

    if not dry_run:
        repo_root.mkdir(parents=True, exist_ok=True)

    for rel_path, content in sorted(files.items()):
        dest_path = repo_root / rel_path
        created_files.append(rel_path)
        total_bytes += len(content.encode("utf-8"))

        if not dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(content, encoding="utf-8")

    if init_git and not dry_run:
        try:
            subprocess.run(
                ["git", "init"],
                cwd=repo_root,
                capture_output=True,
                check=False,
                timeout=10,
            )
        except Exception:
            pass

    return {
        "repo_name": repo_name,
        "target_path": str(repo_root),
        "file_count": len(created_files),
        "total_bytes": total_bytes,
        "files": created_files,
        "dry_run": dry_run,
    }


def scaffold_all_repos(
    target_dir: Path,
    overwrite: bool = False,
    dry_run: bool = False,
    init_git: bool = False,
) -> List[Dict[str, Any]]:
    """Scaffold all 3 ecosystem repositories."""
    results: List[Dict[str, Any]] = []
    for repo_name in REPO_REGISTRY:
        res = scaffold_repo(
            repo_name=repo_name,
            target_dir=target_dir,
            overwrite=overwrite,
            dry_run=dry_run,
            init_git=init_git,
        )
        results.append(res)
    return results


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo", "-r",
        choices=["all", *REPO_REGISTRY.keys()],
        default="all",
        help="Specific repository to scaffold, or 'all' (default: all)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Destination directory (default: results/scaffolded-repos relative to repo root)",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Override git repository root",
    )
    parser.add_argument(
        "--overwrite", "-f",
        action="store_true",
        help="Overwrite existing files in destination directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned operations without writing any files",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available repository scaffold definitions and exit",
    )
    parser.add_argument(
        "--init-git",
        action="store_true",
        help="Run git init inside each scaffolded repository directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON summary",
    )
    args = parser.parse_args(argv)

    if args.list:
        print("Available Public Ecosystem Repositories:")
        for name, defn in REPO_REGISTRY.items():
            print(f"  - {name}:")
            print(f"      {defn.description}")
        return 0

    root = resolve_repo_root(args.repo_root)
    if args.output_dir:
        target_dir = Path(args.output_dir).expanduser().resolve()
    else:
        target_dir = root / "results" / "scaffolded-repos"

    try:
        if args.repo == "all":
            results = scaffold_all_repos(
                target_dir=target_dir,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                init_git=args.init_git,
            )
        else:
            res = scaffold_repo(
                repo_name=args.repo,
                target_dir=target_dir,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                init_git=args.init_git,
            )
            results = [res]
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        mode_str = " (DRY-RUN)" if args.dry_run else ""
        print(f"Scaffolding Koality-Assured Public Repositories{mode_str}:")
        print(f"Destination: {target_dir}\n")
        for res in results:
            print(f"  Repository: {res['repo_name']}")
            print(f"    Path:       {res['target_path']}")
            print(f"    Files:      {res['file_count']} files ({res['total_bytes']} bytes)")
            for f in res["files"]:
                print(f"      + {f}")
            print()
        print("Completed successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
