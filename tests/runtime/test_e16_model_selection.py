"""E1.6.2 UMAL / ModelSelector verification.

Deterministic capability-based model selection. EngineeringWorker must not
contain provider/model selection logic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.models import Capability, HealthStatus, ModelManager, ModelRecord, SelectionRequest
from runtime.models.exceptions import NoCompatibleModelError
from runtime.models.registry import ModelRegistry
from runtime.models.selection import ModelSelector

ROOT = Path(__file__).parents[2]


def _selector_with(models: list[ModelRecord], fallback_order=()):
    registry = ModelRegistry()
    for model in models:
        registry.add_model(model)
    return ModelSelector(registry, fallback_order)


def _model(model_id, provider="test-provider", protocol="openai-compatible", capabilities=(), local=False, priority=0, status=HealthStatus.HEALTHY):
    return ModelRecord(
        id=model_id,
        display_name=model_id,
        provider=provider,
        protocol=protocol,
        capabilities=frozenset(capabilities),
        local=local,
        priority=priority,
        status=status,
    )


def test_coding_capability_selection():
    """Coding task selects a model with CODING capability."""
    selector = _selector_with([
        _model("coder", capabilities=[Capability.CODING], priority=10),
        _model("reasoner", capabilities=[Capability.REASONING], priority=100),
    ])
    selected = selector.select(SelectionRequest(capabilities=frozenset({Capability.CODING})))
    assert selected.id == "coder"


def test_reasoning_capability_selection():
    """Reasoning task selects a model with REASONING capability."""
    selector = _selector_with([
        _model("coder", capabilities=[Capability.CODING], priority=10),
        _model("reasoner", capabilities=[Capability.REASONING], priority=100),
    ])
    selected = selector.select(SelectionRequest(capabilities=frozenset({Capability.REASONING})))
    assert selected.id == "reasoner"


def test_local_model_preference():
    """local_preference=True prefers local models when compatible."""
    selector = _selector_with([
        _model("cloud-model", capabilities=[Capability.CODING], local=False, priority=100),
        _model("local-model", capabilities=[Capability.CODING], local=True, priority=1),
    ])
    selected = selector.select(SelectionRequest(
        capabilities=frozenset({Capability.CODING}), local_preference=True
    ))
    assert selected.id == "local-model"


def test_local_only_restriction():
    """local_only=True excludes cloud models."""
    selector = _selector_with([
        _model("cloud-model", capabilities=[Capability.CODING], local=False),
        _model("local-model", capabilities=[Capability.CODING], local=True),
    ])
    selected = selector.select(SelectionRequest(
        capabilities=frozenset({Capability.CODING}), local_only=True
    ))
    assert selected.id == "local-model"


def test_provider_restriction():
    """provider=... restricts selection to that provider."""
    selector = _selector_with([
        _model("provider-a-model", provider="provider-a", capabilities=[Capability.CODING], priority=100),
        _model("provider-b-model", provider="provider-b", capabilities=[Capability.CODING], priority=200),
    ])
    selected = selector.select(SelectionRequest(
        capabilities=frozenset({Capability.CODING}), provider="provider-a"
    ))
    assert selected.id == "provider-a-model"


def test_unavailable_capability_raises():
    """Requesting a capability no model provides raises NoCompatibleModelError."""
    selector = _selector_with([
        _model("coder", capabilities=[Capability.CODING]),
    ])
    with pytest.raises(NoCompatibleModelError):
        selector.select(SelectionRequest(capabilities=frozenset({Capability.VISION})))


def test_unavailable_model_protocol_raises():
    """Restricting to an unavailable protocol raises NoCompatibleModelError."""
    selector = _selector_with([
        _model("coder", capabilities=[Capability.CODING], protocol="openai-compatible"),
    ])
    with pytest.raises(NoCompatibleModelError):
        selector.select(SelectionRequest(
            capabilities=frozenset({Capability.CODING}), protocol="gemini"
        ))


def test_multiple_compatible_models_deterministic():
    """Multiple compatible models select deterministically (stable tie-break)."""
    models = [
        _model("model-b", capabilities=[Capability.CODING], priority=50),
        _model("model-a", capabilities=[Capability.CODING], priority=50),
        _model("model-c", capabilities=[Capability.CODING], priority=50),
    ]
    selector = _selector_with(models)
    req = SelectionRequest(capabilities=frozenset({Capability.CODING}))
    # Run multiple times to confirm stability.
    first = selector.select(req).id
    for _ in range(10):
        assert selector.select(req).id == first


def test_engineering_worker_has_no_selection_logic():
    """EngineeringWorkerEngine imports no ModelSelector/ModelManager selection."""
    import inspect
    from runtime.engineering.engine import EngineeringWorkerEngine

    source = inspect.getsource(EngineeringWorkerEngine)
    # It may receive an invocation_engine but must not call select_best_model
    # or instantiate a ModelSelector itself.
    assert "select_best_model" not in source
    assert "ModelSelector(" not in source
