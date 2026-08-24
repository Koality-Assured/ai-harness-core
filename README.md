# Koality-Assured AI Harness Core

Decoupled, bare-metal AI agent harness engine for multi-agent routing, context firebreaks, prompt caching, and sandboxed agent-to-agent (A2A) execution.

## Mission Statement

Provide a clean, embeddable, framework-agnostic core engine that brings production-grade multi-agent orchestration, worktree isolation, multi-vendor prompt caching, and dual-retrieval (BM25 + ast-grep) to any software repository.

## Architecture Overview

The harness engine is structured into standalone, decoupled subsystems:

```
harness/
├── __init__.py
├── config.py              # Configuration manifest loader & path resolver
├── isolation/
│   └── worktree.py        # Concurrency-safe Git worktree isolation lifecycle
├── a2a/
│   └── protocol.py        # Sandboxed A2A protocol (8-exchange budget & envelope validation)
├── cache/
│   └── manager.py         # Multi-vendor prompt caching (Anthropic, OpenAI, Gemini)
├── adapters/
│   ├── qmd.py             # Lexical/semantic search adapter
│   ├── ast_grep.py        # Structural AST outline & symbol inspection adapter
│   └── headroom.py        # Headroom context compression proxy client (port 8787)
└── cli/
    └── harness_init.py    # Bootstrap scaffolding CLI for new repositories
```

## Quick Start: Initialize in Any Repository

```bash
# Initialize harness folder skeleton and configuration in the current repository
python -m harness.cli.harness_init

# Initialize in a specific target directory
python -m harness.cli.harness_init --target-dir /path/to/repo
```

## Verification & Testing

```bash
python -m unittest discover -s tests -v
```

## Security Notice

All agent-to-agent exchanges and worktree executions operate under strict security boundaries with explicit token ceilings, input/output validation envelopes, and an 8-exchange budget limit.

## License

MIT License Copyright (c) 2026 Koality-Assured.
