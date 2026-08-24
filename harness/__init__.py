"""Bare-metal .harness engine.

Decoupled core harness providing configuration, worktree isolation, A2A protocols,
tool adapters (QMD, ast-grep, Headroom), and multi-vendor prompt caching.
"""

from .a2a import (
    A2ABudgetExceededError,
    A2ABudgetTracker,
    A2AExchange,
    A2AExchangeSession,
    A2AProtocol,
    A2AProtocolError,
    A2AResultEnvelope,
    A2ASecurityError,
    A2AValidationError,
)
from .adapters import (
    AstGrepAdapter,
    AstGrepError,
    AstGrepMatch,
    AstGrepSymbol,
    HeadroomAdapter,
    HeadroomCompressResult,
    HeadroomError,
    QMDAdapter,
    QMDError,
    QMDHit,
)
from .cache import (
    CacheBreakpoint,
    CacheOptimizationResult,
    PromptCacheManager,
)
from .config import (
    A2AConfig,
    AdaptersConfig,
    AnthropicCacheConfig,
    AstGrepAdapterConfig,
    CacheConfig,
    GeminiCacheConfig,
    GitAdapterConfig,
    HarnessConfig,
    HeadroomAdapterConfig,
    OpenAICacheConfig,
    PathManifestConfig,
    QMDAdapterConfig,
    load_harness_config,
)
from .isolation import (
    WorktreeClaim,
    WorktreeConcurrencyError,
    WorktreeError,
    WorktreeExistsError,
    WorktreeManager,
    WorktreeNotFoundError,
)

__version__ = "0.1.0"

__all__ = [
    "A2ABudgetExceededError",
    "A2ABudgetTracker",
    "A2AConfig",
    "A2AExchange",
    "A2AExchangeSession",
    "A2AProtocol",
    "A2AProtocolError",
    "A2AResultEnvelope",
    "A2ASecurityError",
    "A2AValidationError",
    "AdaptersConfig",
    "AnthropicCacheConfig",
    "AstGrepAdapter",
    "AstGrepAdapterConfig",
    "AstGrepError",
    "AstGrepMatch",
    "AstGrepSymbol",
    "CacheBreakpoint",
    "CacheConfig",
    "CacheOptimizationResult",
    "GeminiCacheConfig",
    "GitAdapterConfig",
    "HarnessConfig",
    "HeadroomAdapter",
    "HeadroomAdapterConfig",
    "HeadroomCompressResult",
    "HeadroomError",
    "OpenAICacheConfig",
    "PathManifestConfig",
    "PromptCacheManager",
    "QMDAdapter",
    "QMDAdapterConfig",
    "QMDError",
    "QMDHit",
    "WorktreeClaim",
    "WorktreeConcurrencyError",
    "WorktreeError",
    "WorktreeExistsError",
    "WorktreeManager",
    "WorktreeNotFoundError",
    "load_harness_config",
]
