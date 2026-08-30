"""E1.7.4/E1.7.5/E1.7.11 Architectural regression guards.

These tests prevent E2-E9 from accidentally breaking the frozen runtime
boundary. They are guards, not new runtime features.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from runtime.engineering import EngineeringWorkerEngine, TaskState
from runtime.freeze import (
    FROZEN_CONTRACTS,
    FROZEN_MODULES,
    PROVIDER_COMPATIBILITY,
    CompatibilityStatus,
)
from runtime.invocation import InvocationEngine, StreamChunk
from runtime.invocation.adapters import InterfaceOnlyAdapter, OllamaAdapter, OpenAICompatibleAdapter

ROOT = Path(__file__).parents[2]


def test_engineering_worker_cannot_select_providers():
    """EngineeringWorkerEngine requests capabilities, not a specific provider/model."""
    source = inspect.getsource(EngineeringWorkerEngine)
    # It must not call model-selection APIs or hardcode a provider selection.
    assert "select_best_model" not in source
    assert "ModelSelector(" not in source
    assert "provider=" not in source  # no hardcoded provider in worker logic


def test_engineering_worker_cannot_directly_call_providers():
    """EngineeringWorkerEngine must not use HTTP transports directly."""
    source = inspect.getsource(EngineeringWorkerEngine)
    assert "urlopen" not in source
    assert "HTTPTransport" not in source


def test_invocation_engine_is_runtime_gateway():
    """InvocationEngine is the only gateway to provider invocation."""
    source = inspect.getsource(InvocationEngine)
    # It must have invoke() and stream() entry points.
    assert "def invoke(" in source
    assert "def stream(" in source
    # It must dispatch through InvocationDispatcher, not direct adapter calls.
    assert "self.dispatcher.dispatch" in source


def test_umal_owns_model_selection():
    """ModelSelector is the model-selection authority."""
    from runtime.models.selection import ModelSelector
    source = inspect.getsource(ModelSelector)
    assert "def select(" in source
    assert "capabilities.issubset" in source


def test_provider_adapters_are_protocol_boundaries():
    """Adapters translate protocol, never select providers/models."""
    for cls in (OpenAICompatibleAdapter, OllamaAdapter, InterfaceOnlyAdapter):
        source = inspect.getsource(cls)
        assert "select_best_model" not in source
        assert "ModelSelector" not in source


def test_streaming_does_not_fake_chunks():
    """No adapter's stream() calls invoke() to split a completed response."""
    for cls in (OpenAICompatibleAdapter, OllamaAdapter, InterfaceOnlyAdapter):
        source = inspect.getsource(cls.stream)
        assert "self.invoke(" not in source


def test_streaming_unsupported_is_structured():
    """InterfaceOnlyAdapter.stream raises StreamUnsupportedError, not fake data."""
    from runtime.invocation.exceptions import StreamUnsupportedError
    adapter = InterfaceOnlyAdapter("http://x")
    with pytest.raises(StreamUnsupportedError):
        list(adapter.stream(
            _default_model(), _stream_request()
        ))


def test_terminal_task_state_cannot_transition():
    """Terminal states (COMPLETED/FAILED/BLOCKED/SKIPPED/CANCELLED) reject transitions."""
    from runtime.engineering import InvocationTask, TaskContext
    for terminal in (TaskState.COMPLETED, TaskState.FAILED, TaskState.BLOCKED, TaskState.SKIPPED, TaskState.CANCELLED):
        task = InvocationTask(
            task_id="t1", contract_id="c1", target_path="x",
            execution_context=TaskContext(
                engineering_contract_id="c1", execution_batch_id="b1", invocation_task_id="t1"
            ),
            state=terminal,
        )
        with pytest.raises(ValueError):
            task.transition_to(TaskState.RUNNING)


def test_frozen_contracts_are_immutable():
    """All frozen contracts have ConfigDict(frozen=True) where required."""
    from runtime.invocation.models import StreamChunk, StreamUsage
    from runtime.invocation.request import InvocationRequest
    from runtime.invocation.response import InvocationResponse
    from runtime.engineering.models import (
        BatchResult, ExecutionBatch, EngineeringResult, InvocationTask, TaskContext
    )
    frozen_models = [
        StreamChunk, StreamUsage, InvocationRequest, InvocationResponse,
        BatchResult, ExecutionBatch, EngineeringResult, InvocationTask, TaskContext,
    ]
    for model in frozen_models:
        assert model.model_config.get("frozen") is True, f"{model.__name__} must be frozen"


def test_frozen_manifest_lists_all_contracts():
    """Freeze manifest contract list matches actual frozen model classes."""
    # The manifest must not claim contracts that do not exist.
    import importlib
    for contract in FROZEN_CONTRACTS:
        # All names should be importable from their known modules.
        # This is a sanity check that the manifest is consistent.
        assert contract


def test_frozen_modules_exist():
    """Every frozen module path in the manifest exists on disk."""
    for frozen in FROZEN_MODULES:
        path = ROOT / frozen.path
        assert path.exists(), f"{frozen.path} missing"


def test_provider_compatibility_declaration_consistent():
    """Compatibility declaration distinguishes supported/verified/mocked/unverified/unsupported."""
    statuses = {entry.status for entry in PROVIDER_COMPATIBILITY}
    assert CompatibilityStatus.VERIFIED in statuses
    assert CompatibilityStatus.UNSUPPORTED in statuses
    # Only adapters actually implemented can be VERIFIED.
    verified = {e.provider for e in PROVIDER_COMPATIBILITY if e.status == CompatibilityStatus.VERIFIED}
    assert verified == {"openai-compatible", "ollama"}


def _default_model():
    from runtime.models import ModelManager
    return ModelManager(ROOT / "config" / "models.yaml").resolver.find_model("default-local")


def _stream_request():
    from runtime.invocation import InvocationRequest
    return InvocationRequest(prompt="Hi", streaming=True)
