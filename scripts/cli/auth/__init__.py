"""Harness CLI Authentication & Keyring Subsystem.

tags: [harness, cli, auth, keyring, oauth]
routing_hints: [auth, keyring, oauth, token, credentials]
"""

from __future__ import annotations

from .keyring_vault import (
    EncryptedFileVault,
    KeyringVault,
    UniversalVault,
    get_vault,
    is_token_expired,
    mask_token,
)
from .oauth_flows import (
    AnthropicOAuthFlow,
    CursorAuthFlow,
    GeminiOAuthFlow,
    LoopbackAuthServer,
    OpenAIAuthFlow,
    generate_pkce_pair,
)

__all__ = [
    "AnthropicOAuthFlow",
    "CursorAuthFlow",
    "EncryptedFileVault",
    "GeminiOAuthFlow",
    "KeyringVault",
    "LoopbackAuthServer",
    "OpenAIAuthFlow",
    "UniversalVault",
    "generate_pkce_pair",
    "get_vault",
    "is_token_expired",
    "mask_token",
]
