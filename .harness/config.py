"""Configuration parser and validator for the bare-metal .harness engine.

Loads config/harness.config.json or provides structured fallback defaults.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PathManifestConfig:
    """Configurable path manifests for skills, agents, memory, worktrees, docs, and routing."""

    skills: str = "ai-tooling/skills"
    agents: str = "ai-tooling/agents"
    memory: str = "scratch/memory"  # Template default for new repos; this router overrides to ai-tooling/memory.
    worktrees: str = "scratch/worktrees"
    docs: str = "docs"
    routing: str = "routing"

    def resolve(self, key: str, repo_root: Path) -> Path:
        """Resolve a relative manifest path against repo root."""
        val = getattr(self, key, None)
        if val is None:
            raise KeyError(f"Unknown path manifest key: {key}")
        return (repo_root / val).resolve()


@dataclass
class QMDAdapterConfig:
    """Tool adapter settings for QMD semantic search."""

    command: str = "qmd"
    default_min_score: float = 0.5
    default_limit: int = 5
    collections: list[str] = field(
        default_factory=lambda: [
            "routing",
            "docs",
            "projects",
            "references",
            "research",
            "supporting",
            "ai-tooling",
            "scripts",
            "actionable",
            "results",
        ]
    )
    timeout_sec: int = 60


@dataclass
class AstGrepAdapterConfig:
    """Tool adapter settings for ast-grep AST search and outline."""

    command: str = "ast-grep"
    timeout_sec: int = 60
    default_languages: list[str] = field(
        default_factory=lambda: [
            "python",
            "typescript",
            "javascript",
            "json",
            "yaml",
            "markdown",
        ]
    )


@dataclass
class HeadroomAdapterConfig:
    """Tool adapter settings for Headroom compression proxy."""

    base_url: str = "http://127.0.0.1:8787"
    port: int = 8787
    timeout_sec: int = 15
    enabled: bool = True


@dataclass
class GitAdapterConfig:
    """Tool adapter settings for Git worktree and branch management."""

    command: str = "git"
    timeout_sec: int = 30
    branch_prefix: str = "agent"


@dataclass
class AdaptersConfig:
    """Container for all tool adapter configurations."""

    qmd: QMDAdapterConfig = field(default_factory=QMDAdapterConfig)
    ast_grep: AstGrepAdapterConfig = field(default_factory=AstGrepAdapterConfig)
    headroom: HeadroomAdapterConfig = field(default_factory=HeadroomAdapterConfig)
    git: GitAdapterConfig = field(default_factory=GitAdapterConfig)


@dataclass
class AnthropicCacheConfig:
    """Anthropic prompt cache settings (max 4 breakpoints, 5m TTL)."""

    max_breakpoints: int = 4
    ttl_seconds: int = 300
    min_tokens_threshold: int = 1024


@dataclass
class OpenAICacheConfig:
    """OpenAI prompt cache settings (1024 token minimum prefix)."""

    min_tokens_prefix: int = 1024
    prefix_alignment_tokens: int = 128


@dataclass
class GeminiCacheConfig:
    """Gemini context cache settings (32k token threshold)."""

    min_tokens_threshold: int = 32768
    default_ttl_seconds: int = 3600
    mode: str = "context_cache"


@dataclass
class CacheConfig:
    """Multi-vendor cache configuration."""

    anthropic: AnthropicCacheConfig = field(default_factory=AnthropicCacheConfig)
    openai: OpenAICacheConfig = field(default_factory=OpenAICacheConfig)
    gemini: GeminiCacheConfig = field(default_factory=GeminiCacheConfig)


@dataclass
class A2AConfig:
    """Agent-to-Agent protocol configuration."""

    default_budget: int = 8
    max_budget: int = 24
    require_clean_state: bool = True
    disallow_destructive: bool = True


@dataclass
class HostAdaptersConfig:
    """Project-level configuration paths for multi-vendor host adapters."""

    claude_settings: str = ".claude/settings.json"
    claude_rules: str = "CLAUDE.md"
    cursor_rules_dir: str = ".cursor/rules"
    cursor_ignore: str = ".cursorignore"
    copilot_instructions: str = ".github/copilot-instructions.md"
    gemini_rules: str = "GEMINI.md"


@dataclass
class SubagentsConfig:
    """Subagent context isolation and boundary configuration."""

    isolate_parent_context: bool = True
    clean_slate_required: bool = True
    prohibit_transcript_forwarding: bool = True
    enforce_selective_retrieval: bool = True
    host_adapters: HostAdaptersConfig = field(default_factory=HostAdaptersConfig)


@dataclass
class HarnessConfig:
    """Root configuration model for the .harness engine."""

    version: str = "1.0.0"
    paths: PathManifestConfig = field(default_factory=PathManifestConfig)
    adapters: AdaptersConfig = field(default_factory=AdaptersConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    a2a: A2AConfig = field(default_factory=A2AConfig)
    subagents: SubagentsConfig = field(default_factory=SubagentsConfig)
    repo_root: Path = field(default_factory=Path.cwd)

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to a dictionary."""
        data = asdict(self)
        data["repo_root"] = str(self.repo_root)
        return data

    def to_json(self, indent: int = 2) -> str:
        """Serialize configuration to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def validate(self) -> list[str]:
        """Validate configuration settings and return list of validation errors."""
        errors: list[str] = []

        # Anthropic breakpoint validation
        if not (1 <= self.cache.anthropic.max_breakpoints <= 4):
            errors.append(
                f"Anthropic max_breakpoints must be between 1 and 4, got {self.cache.anthropic.max_breakpoints}"
            )
        if self.cache.anthropic.ttl_seconds < 0:
            errors.append("Anthropic ttl_seconds cannot be negative")
        if self.cache.anthropic.min_tokens_threshold < 0:
            errors.append("Anthropic min_tokens_threshold cannot be negative")

        # OpenAI validation
        if self.cache.openai.min_tokens_prefix < 0:
            errors.append("OpenAI min_tokens_prefix cannot be negative")
        if self.cache.openai.prefix_alignment_tokens <= 0:
            errors.append("OpenAI prefix_alignment_tokens must be positive")

        # Gemini validation
        if self.cache.gemini.min_tokens_threshold < 0:
            errors.append("Gemini min_tokens_threshold cannot be negative")
        if self.cache.gemini.default_ttl_seconds <= 0:
            errors.append("Gemini default_ttl_seconds must be positive")

        # A2A validation
        if self.a2a.default_budget <= 0:
            errors.append("A2A default_budget must be greater than 0")
        if self.a2a.max_budget < self.a2a.default_budget:
            errors.append("A2A max_budget must be greater than or equal to default_budget")

        # Adapters validation
        if self.adapters.qmd.timeout_sec <= 0:
            errors.append("QMD timeout_sec must be positive")
        if self.adapters.ast_grep.timeout_sec <= 0:
            errors.append("ast-grep timeout_sec must be positive")
        if self.adapters.headroom.timeout_sec <= 0:
            errors.append("Headroom timeout_sec must be positive")
        if not (1 <= self.adapters.headroom.port <= 65535):
            errors.append(f"Invalid Headroom port: {self.adapters.headroom.port}")

        return errors


def _build_path_manifest(data: dict[str, Any] | None) -> PathManifestConfig:
    if not data:
        return PathManifestConfig()
    return PathManifestConfig(
        skills=str(data.get("skills", "ai-tooling/skills")),
        agents=str(data.get("agents", "ai-tooling/agents")),
        memory=str(data.get("memory", "scratch/memory")),
        worktrees=str(data.get("worktrees", "scratch/worktrees")),
        docs=str(data.get("docs", "docs")),
        routing=str(data.get("routing", "routing")),
    )


def _build_adapters(data: dict[str, Any] | None) -> AdaptersConfig:
    if not data:
        return AdaptersConfig()
    qmd_data = data.get("qmd", {})
    ast_data = data.get("ast_grep", {})
    hr_data = data.get("headroom", {})
    git_data = data.get("git", {})

    qmd = QMDAdapterConfig(
        command=str(qmd_data.get("command", "qmd")),
        default_min_score=float(qmd_data.get("default_min_score", 0.5)),
        default_limit=int(qmd_data.get("default_limit", 5)),
        collections=list(qmd_data.get("collections", QMDAdapterConfig().collections)),
        timeout_sec=int(qmd_data.get("timeout_sec", 60)),
    )

    ast_grep = AstGrepAdapterConfig(
        command=str(ast_data.get("command", "ast-grep")),
        timeout_sec=int(ast_data.get("timeout_sec", 60)),
        default_languages=list(ast_data.get("default_languages", AstGrepAdapterConfig().default_languages)),
    )

    headroom = HeadroomAdapterConfig(
        base_url=str(hr_data.get("base_url", "http://127.0.0.1:8787")),
        port=int(hr_data.get("port", 8787)),
        timeout_sec=int(hr_data.get("timeout_sec", 15)),
        enabled=bool(hr_data.get("enabled", True)),
    )

    git = GitAdapterConfig(
        command=str(git_data.get("command", "git")),
        timeout_sec=int(git_data.get("timeout_sec", 30)),
        branch_prefix=str(git_data.get("branch_prefix", "agent")),
    )

    return AdaptersConfig(qmd=qmd, ast_grep=ast_grep, headroom=headroom, git=git)


def _build_cache(data: dict[str, Any] | None) -> CacheConfig:
    if not data:
        return CacheConfig()
    anthropic_data = data.get("anthropic", {})
    openai_data = data.get("openai", {})
    gemini_data = data.get("gemini", {})

    anthropic = AnthropicCacheConfig(
        max_breakpoints=int(anthropic_data.get("max_breakpoints", 4)),
        ttl_seconds=int(anthropic_data.get("ttl_seconds", 300)),
        min_tokens_threshold=int(anthropic_data.get("min_tokens_threshold", 1024)),
    )

    openai = OpenAICacheConfig(
        min_tokens_prefix=int(openai_data.get("min_tokens_prefix", 1024)),
        prefix_alignment_tokens=int(openai_data.get("prefix_alignment_tokens", 128)),
    )

    gemini = GeminiCacheConfig(
        min_tokens_threshold=int(gemini_data.get("min_tokens_threshold", 32768)),
        default_ttl_seconds=int(gemini_data.get("default_ttl_seconds", 3600)),
        mode=str(gemini_data.get("mode", "context_cache")),
    )

    return CacheConfig(anthropic=anthropic, openai=openai, gemini=gemini)


def _build_a2a(data: dict[str, Any] | None) -> A2AConfig:
    if not data:
        return A2AConfig()
    return A2AConfig(
        default_budget=int(data.get("default_budget", 8)),
        max_budget=int(data.get("max_budget", 24)),
        require_clean_state=bool(data.get("require_clean_state", True)),
        disallow_destructive=bool(data.get("disallow_destructive", True)),
    )


def _build_subagents(data: dict[str, Any] | None) -> SubagentsConfig:
    if not data:
        return SubagentsConfig()
    adapters_data = data.get("host_adapters", {})
    host_adapters = HostAdaptersConfig(
        claude_settings=str(adapters_data.get("claude", {}).get("settings_path", ".claude/settings.json")),
        claude_rules=str(adapters_data.get("claude", {}).get("rules_entry", "CLAUDE.md")),
        cursor_rules_dir=str(adapters_data.get("cursor", {}).get("rules_dir", ".cursor/rules")),
        cursor_ignore=str(adapters_data.get("cursor", {}).get("ignore_path", ".cursorignore")),
        copilot_instructions=str(adapters_data.get("openai_copilot", {}).get("instructions_path", ".github/copilot-instructions.md")),
        gemini_rules=str(adapters_data.get("antigravity", {}).get("rules_entry", "GEMINI.md")),
    )
    return SubagentsConfig(
        isolate_parent_context=bool(data.get("isolate_parent_context", True)),
        clean_slate_required=bool(data.get("clean_slate_required", True)),
        prohibit_transcript_forwarding=bool(data.get("prohibit_transcript_forwarding", True)),
        enforce_selective_retrieval=bool(data.get("enforce_selective_retrieval", True)),
        host_adapters=host_adapters,
    )


def load_harness_config(
    config_path: Path | str | None = None,
    repo_root: Path | str | None = None,
) -> HarnessConfig:
    """Load HarnessConfig from JSON file or return fallback defaults."""
    resolved_root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()

    target_file: Path | None = None
    if config_path:
        p = Path(config_path)
        target_file = p if p.is_absolute() else resolved_root / p
    else:
        candidates = [
            resolved_root / "config" / "harness.config.json",
            resolved_root / ".harness" / "harness.config.json",
            resolved_root / "harness.config.json",
        ]
        for cand in candidates:
            if cand.is_file():
                target_file = cand
                break

    if target_file and target_file.is_file():
        try:
            content = json.loads(target_file.read_text(encoding="utf-8"))
            version = str(content.get("version", "1.0.0"))
            paths = _build_path_manifest(content.get("paths"))
            adapters = _build_adapters(content.get("adapters"))
            cache = _build_cache(content.get("cache"))
            a2a = _build_a2a(content.get("a2a"))
            subagents = _build_subagents(content.get("subagents"))

            cfg = HarnessConfig(
                version=version,
                paths=paths,
                adapters=adapters,
                cache=cache,
                a2a=a2a,
                subagents=subagents,
                repo_root=resolved_root,
            )
            val_errors = cfg.validate()
            if val_errors:
                raise ValueError(f"Invalid harness configuration: {'; '.join(val_errors)}")
            return cfg
        except json.JSONDecodeError:
            # If JSON is corrupted, fallback with root
            return HarnessConfig(repo_root=resolved_root)
        except ValueError:
            # Re-raise explicit validation errors
            raise

    return HarnessConfig(repo_root=resolved_root)
