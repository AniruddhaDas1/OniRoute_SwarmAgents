"""E1.7 Runtime Kernel Freeze Manifest (machine-readable).

Deterministic inventory of frozen E1 runtime contracts, boundaries, and
compatibility status. This module is documentation-as-code: it does not
execute runtime behavior, but it provides a verifiable source of truth for
E2-E9 integration and future freeze audits.

Do NOT modify these constants to claim new capabilities. If a contract
changes, update this manifest in the same commit as the contract change.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import FrozenSet, Tuple


ONIROUTE_VERSION = "v1.2.1"
RUNTIME_VERSION = "v1.2.1-e1.7"
FREEZE_PHASE = "E1.7"


class ContractStatus(StrEnum):
    PUBLIC_CONTRACT = "PUBLIC_CONTRACT"
    INTERNAL_IMPLEMENTATION = "INTERNAL_IMPLEMENTATION"
    FROZEN = "FROZEN"
    EXTENSIBLE = "EXTENSIBLE"


class CompatibilityStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    MOCK_VERIFIED = "MOCK-VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class FrozenModule:
    path: str
    status: ContractStatus
    notes: str = ""


@dataclass(frozen=True)
class ProviderCompatibility:
    provider: str
    status: CompatibilityStatus
    evidence: str


FROZEN_MODULES: Tuple[FrozenModule, ...] = (
    FrozenModule("runtime/invocation/request.py", ContractStatus.FROZEN, "InvocationRequest public contract"),
    FrozenModule("runtime/invocation/response.py", ContractStatus.FROZEN, "InvocationResponse public contract"),
    FrozenModule("runtime/invocation/models.py", ContractStatus.FROZEN, "Message, Usage, StreamChunk, StreamUsage, StreamFinishReason"),
    FrozenModule("runtime/invocation/engine.py", ContractStatus.FROZEN, "InvocationEngine invoke/stream gateway"),
    FrozenModule("runtime/invocation/router.py", ContractStatus.FROZEN, "InvocationRouter -> UMAL ModelSelector"),
    FrozenModule("runtime/invocation/dispatcher.py", ContractStatus.FROZEN, "Protocol adapter dispatch"),
    FrozenModule("runtime/invocation/adapters.py", ContractStatus.FROZEN, "OpenAI-compatible + Ollama + InterfaceOnly adapters"),
    FrozenModule("runtime/invocation/streaming.py", ContractStatus.FROZEN, "StreamResponse + assemble_stream"),
    FrozenModule("runtime/invocation/fallback.py", ContractStatus.FROZEN, "FallbackChain ordering utility"),
    FrozenModule("runtime/invocation/retry.py", ContractStatus.FROZEN, "RetryPolicy + with_retry (bounded fail-fast)"),
    FrozenModule("runtime/invocation/exceptions.py", ContractStatus.FROZEN, "InvocationError hierarchy"),
    FrozenModule("runtime/invocation/protocols.py", ContractStatus.FROZEN, "ProtocolAdapter interface"),
    FrozenModule("runtime/models/capabilities.py", ContractStatus.FROZEN, "Capability enum"),
    FrozenModule("runtime/models/models.py", ContractStatus.FROZEN, "ModelRecord, ProviderRecord, ProtocolRecord, SelectionRequest"),
    FrozenModule("runtime/models/selection.py", ContractStatus.FROZEN, "ModelSelector scoring"),
    FrozenModule("runtime/models/registry.py", ContractStatus.FROZEN, "ModelRegistry"),
    FrozenModule("runtime/models/catalog.py", ContractStatus.FROZEN, "ModelCatalog load"),
    FrozenModule("runtime/models/manager.py", ContractStatus.FROZEN, "ModelManager facade"),
    FrozenModule("runtime/models/resolver.py", ContractStatus.FROZEN, "ModelResolver"),
    FrozenModule("runtime/models/exceptions.py", ContractStatus.FROZEN, "ModelLayerError hierarchy"),
    FrozenModule("runtime/engineering/models.py", ContractStatus.FROZEN, "TaskState, TaskContext, InvocationTask, ExecutionBatch, BatchResult, EngineeringResult"),
    FrozenModule("runtime/engineering/engine.py", ContractStatus.FROZEN, "InvocationPlanner, ResponseAggregator, EngineeringWorkerEngine"),
    FrozenModule("runtime/engineering/exceptions.py", ContractStatus.FROZEN, "Engineering error hierarchy"),
    FrozenModule("runtime/experience/models.py", ContractStatus.FROZEN, "StreamEvent, StreamEventType (incl. STREAM_*)"),
    FrozenModule("runtime/verification/capability_matrix.py", ContractStatus.FROZEN, "E1.6 verification matrix"),
)


FROZEN_CONTRACTS: Tuple[str, ...] = (
    "InvocationRequest",
    "InvocationResponse",
    "Message",
    "ToolRequest",
    "ToolCall",
    "Usage",
    "StreamChunk",
    "StreamUsage",
    "StreamFinishReason",
    "SelectionRequest",
    "ModelRecord",
    "ProviderRecord",
    "ProtocolRecord",
    "HealthStatus",
    "Capability",
    "TaskState",
    "TaskContext",
    "InvocationTask",
    "ExecutionBatch",
    "BatchResult",
    "EngineeringFailure",
    "EngineeringResult",
    "StreamEvent",
    "StreamEventType",
)


PROVIDER_COMPATIBILITY: Tuple[ProviderCompatibility, ...] = (
    ProviderCompatibility("openai-compatible", CompatibilityStatus.VERIFIED, "E1.5/E1.6 deterministic SSE + non-streaming tests"),
    ProviderCompatibility("ollama", CompatibilityStatus.VERIFIED, "E1.5/E1.6 deterministic ndjson + non-streaming tests"),
    ProviderCompatibility("mock (two-provider interoperability)", CompatibilityStatus.MOCK_VERIFIED, "E1.6 mocked decoupling test"),
    ProviderCompatibility("custom (InterfaceOnly)", CompatibilityStatus.UNSUPPORTED, "No real streaming or non-streaming implementation"),
    ProviderCompatibility("anthropic", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("gemini", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("google", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("groq", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("deepseek", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("mistral", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("cohere", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("together", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("fireworks", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("hugging-face", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("openrouter", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("vllm", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("lm-studio", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("mlx", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("localai", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("llama-cpp", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("koboldcpp", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
    ProviderCompatibility("tgi", CompatibilityStatus.UNSUPPORTED, "Catalog metadata only, no adapter"),
)


# E1.6 baseline + E1.6 new tests.
E16_BASELINE_TOTAL_TESTS = 757
E16_BASELINE_FAILED = 0
E17_FOCUSED_TEST_COUNT = 66  # test_e16_*.py + freeze guard tests below
E17_GUARD_TEST_COUNT = 20


KNOWN_LIMITATIONS: Tuple[str, ...] = (
    "Only 2 real protocol adapters: OpenAI-compatible and Ollama.",
    "Only 1 configured model: local-metadata-placeholder (custom/local-process).",
    "No automatic provider-failure fallback in InvocationEngine (only fallback_order in ModelSelector + template fallback in EngineeringWorker).",
    "Real provider smoke tests are opt-in, not CI-required.",
    "Tool-calling, vision, and structured-output are declared in catalog metadata but have no adapter implementation in E1.",
)


PROHIBITED_MODIFICATIONS: Tuple[str, ...] = (
    "Do not add a new InvocationEngine or a second streaming engine.",
    "Do not add provider-specific logic inside agents or EngineeringWorker.",
    "Do not add a new UMAL, ModelSelector, or provider registry.",
    "Do not add retries, self-healing, or dynamic contracts in E1.",
    "Do not change frozen contracts without an architectural exception.",
)
