"""E1.6.9 Provider fallback verification.

Verify the EXISTING fallback behavior. Do NOT create a new retry/fallback
architecture. The current repository has:
- `FallbackChain` (a model-ordering utility)
- `fallback_order` in ModelSelector scoring
- `FailurePolicy.FALLBACK` declared in retry.py

But there is NO automatic provider-failure fallback execution in
InvocationEngine. This is a documented verification gap, not an E1.6 defect.
"""

from __future__ import annotations

from pathlib import Path

from runtime.invocation.fallback import FallbackChain

ROOT = Path(__file__).parents[2]


def test_fallback_chain_orders_models():
    """FallbackChain.ordered() puts preferred model first, preserving rest."""
    chain = FallbackChain(("model-b", "model-c"))
    result = chain.ordered(preferred="model-a")
    assert result == ("model-a", "model-b", "model-c")


def test_fallback_chain_no_preferred():
    """Without a preferred model, original order is preserved."""
    chain = FallbackChain(("model-b", "model-c", "model-a"))
    assert chain.ordered() == ("model-b", "model-c", "model-a")


def test_fallback_order_in_model_selector():
    """fallback_order influences ModelSelector scoring deterministically."""
    from runtime.models import Capability, HealthStatus, ModelManager, ModelRecord, SelectionRequest
    from runtime.models.registry import ModelRegistry
    from runtime.models.selection import ModelSelector

    registry = ModelRegistry()
    registry.add_model(ModelRecord(
        id="fallback-model", display_name="Fallback", provider="provider-fb",
        protocol="mock", capabilities=frozenset({Capability.CODING}),
        status=HealthStatus.HEALTHY, priority=100,
    ))
    registry.add_model(ModelRecord(
        id="preferred-model", display_name="Preferred", provider="provider-pref",
        protocol="mock", capabilities=frozenset({Capability.CODING}),
        status=HealthStatus.HEALTHY, priority=100,
    ))
    selector = ModelSelector(registry, fallback_order=("provider-pref", "provider-fb"))
    selected = selector.select(SelectionRequest(capabilities=frozenset({Capability.CODING})))
    assert selected.id == "preferred-model"


def test_automatic_fallback_not_implemented_is_documented_gap():
    """Document that InvocationEngine has no automatic provider-fallback path.

    This test does NOT assert new behavior. It asserts the current state so
    future phases can add fallback without silently breaking verification.
    """
    import inspect
    from runtime.invocation.engine import InvocationEngine

    source = inspect.getsource(InvocationEngine)
    # InvocationEngine.invoke() does not retry with a fallback provider.
    assert "FallbackChain" not in source
    assert "fallback_order" not in source
