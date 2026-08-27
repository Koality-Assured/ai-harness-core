---
doc_kind: supporting
canonical_id: powershell-python-patterns
topics: [powershell, python, windows, scripting]
rag_keywords: [powershell, escaping, quotes, python-c, windows, execution]
---

# PowerShell and Python execution patterns

Durable operating notes and caveats for executing Python, Node/npx, and CLI automation under PowerShell on Windows.

## Quoting and escape caveats

### 1. PowerShell backtick and variable interpolation

PowerShell uses the backtick (`` ` ``) as its escape character and interpolates `$variables` and sub-expressions inside double-quoted strings before the target executable runs. If an inline Python command contains backticks (such as markdown code fences or backtick expressions) inside `python -c "..."`, PowerShell intercepts them and executes sub-commands or drops characters.

### 2. The inline `python -c` escape trap

When running `python -c "..."` inside PowerShell:

- `\a` is parsed by PowerShell or Python escape parsing as ASCII bell, corrupting paths like `\ai-tooling` to `\x07i-tooling`.
- `\r` is parsed as carriage return, corrupting paths like `\routing` to a newline.
- `\t` is parsed as horizontal tab, corrupting words like `\threat-model`.
- Nested triple quotes inside double quotes fail when strings contain single or double quotes.

### 3. Markdown and JSON delimiter collisions

Passing multi-line Markdown or JSON strings directly through terminal command lines risks argument truncation, quote stripping, and syntax errors.

## Proven execution patterns

### Pattern A: Dedicated script files over inline commands

For any task requiring more than 2 lines of Python or containing multi-line strings / markdown:

1. Write the Python logic to a temporary script under `scratch/` (e.g. `scratch/build_artifacts.py`).
2. Execute `python scratch/build_artifacts.py`.
3. Promote durable logic to `scripts/<purpose>/` or delete scratch scripts upon completion.

### Pattern B: Tool-native modifications

For editing or replacing existing file content:

- Use `replace_file_content` instead of terminal regex or ad-hoc shell commands.
- Tool payloads bypass the OS shell entirely, avoiding all quoting and escape corruption.

### Pattern C: Forward slashes everywhere

Always use forward slashes (`/`) for paths across Python, git, npm/npx, and qmd:

```powershell
python scripts/docs/run_markdownlint.py
```

Avoid Windows-style backslashes in code strings and CLI arguments.

### Pattern D: Explicit UTF-8 console encoding

On Windows environments where PowerShell defaults to Windows-1252 or legacy code pages:

- Ensure scripts open files with explicit `encoding="utf-8"`.
- When terminal output contains UTF-8 symbols or non-ASCII characters, configure console encoding at the start of complex sessions:

  ```powershell
  $OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
  ```

### Pattern E: Path quoting for spaces

When invoking CLI tools or Python scripts with arguments that may contain whitespace, enclose paths in single or double quotes and use forward slashes:

```powershell
python scripts/cost-layers/extract_ast_facts.py --target "supporting/powershell"
```

### Pattern F: Workspace vs Artifact tool boundaries (`write_to_file`)

Antigravity's `write_to_file` tool strictly differentiates brain artifacts from workspace files:
- When writing workspace code, tests, or documentation under `[REPO_ROOT]/`, **omit `ArtifactMetadata` entirely**.
- Supplying `ArtifactMetadata` to a workspace path triggers an `invalid_args: not a valid artifact path` error because `ArtifactMetadata` is reserved exclusively for the host brain artifact directory (`<appDataDir>\brain\<conversation-id>`).

### Pattern G: CLI subcommand flags & area registration

1. **Explicit flags over positional arguments**: Scripts such as `spawn_worktree.py remove` require `--slug <slug>` (e.g. `python scripts/routing/spawn_worktree.py remove --slug my-task`). Passing positional arguments causes argparse validation failures.
2. **Area registration gating**: `spawn_worktree.py check` and `add` validate area names strictly against `routing/areas.yaml`. Passing unregistered top-level folders (e.g. `config/`) will fail validation; only use registered area identifiers (`ai-tooling`, `scripts`, `docs`, `results`, etc.).

### Pattern H: Mutation gates and preflight inspection

Mutation scripts that rebuild or touch shared indexes (such as `python scripts/qmd/refresh_qmd_index.py`) enforce safety gates:
- Run the inspection preflight first (`python scripts/qmd/qmd_preflight.py`).
- If refresh is genuinely required, pass `--approved-by-user` explicitly.

