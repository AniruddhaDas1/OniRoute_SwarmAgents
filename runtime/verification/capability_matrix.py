"""Machine-readable provider capability verification matrix (Phase E1.6).

This matrix records ONLY capabilities that are actually implemented in the
repository adapters, not capabilities implied by provider names in the catalog.

Rules:
- `supported` means the adapter code path exists and has deterministic tests.
- `mockable` means behavior can be verified with a deterministic fake transport.
- `unverified` means the code path exists but has no live provider evidence.
- `unsupported` means no adapter implementation exists.

Do NOT edit this table to make claims. Edit adapter code first, then update
the table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class AdapterCapability:
    """Verified capabilities of a single protocol adapter implementation."""

    adapter_class: str
    protocol: str
    non_streaming: bool = False
    streaming: bool = False
    sse_parsing: bool = False
    ndjson_parsing: bool = False
    request_translation: bool = False
    response_translation: bool = False
    error_normalization: bool = False
    auth_header_support: bool = False
    usage_parsing: bool = False
    finish_reason_parsing: bool = False
    model_metadata: bool = False


# What is ACTUALLY implemented in runtime/invocation/adapters.py
IMPLEMENTED_ADAPTERS: FrozenSet[AdapterCapability] = frozenset(
    {
        AdapterCapability(
            adapter_class="OpenAICompatibleAdapter",
            protocol="openai-compatible",
            non_streaming=True,
            streaming=True,
            sse_parsing=True,
            request_translation=True,
            response_translation=True,
            error_normalization=True,
            auth_header_support=True,
            usage_parsing=True,
            finish_reason_parsing=True,
            model_metadata=True,
        ),
        AdapterCapability(
            adapter_class="OllamaAdapter",
            protocol="ollama",
            non_streaming=True,
            streaming=True,
            ndjson_parsing=True,
            request_translation=True,
            response_translation=True,
            error_normalization=True,
            auth_header_support=True,
            usage_parsing=True,
            finish_reason_parsing=True,
            model_metadata=True,
        ),
        AdapterCapability(
            adapter_class="InterfaceOnlyAdapter",
            protocol="custom",
            non_streaming=False,
            streaming=False,
        ),
    }
)


# Provider/model configuration currently loadable from config/models.yaml.
# This is the only configured, selectable model record.
CONFIGURED_MODELS: FrozenSet[str] = frozenset({"local-metadata-placeholder"})

# Providers named in runtime/models/providers.py but WITHOUT a dedicated
# adapter implementation. These are catalog placeholders, not runtime
# integrations.
CATALOG_ONLY_PROVIDERS: FrozenSet[str] = frozenset(
    {
        "openai",
        "anthropic",
        "google",
        "vllm",
        "lm-studio",
        "mlx",
        "localai",
        "llama-cpp",
        "koboldcpp",
        "tgi",
        "groq",
        "together",
        "fireworks",
        "deepseek",
        "mistral",
        "cohere",
        "hugging-face",
        "openrouter",
    }
)

# Protocols named in runtime/models/protocols.py but WITHOUT a dedicated
# adapter implementation.
CATALOG_ONLY_PROTOCOLS: FrozenSet[str] = frozenset(
    {"anthropic", "gemini", "mcp", "http", "python", "cli", "local-process"}
)

# Real provider credentials are never required for deterministic CI.
REAL_PROVIDER_SMOKE_REQUIRED = False
