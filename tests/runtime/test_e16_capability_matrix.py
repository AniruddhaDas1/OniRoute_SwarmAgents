"""E1.6.1 Provider Capability Matrix Verification."""

from __future__ import annotations

from runtime.verification import (
    CATALOG_ONLY_PROTOCOLS,
    CATALOG_ONLY_PROVIDERS,
    CONFIGURED_MODELS,
    IMPLEMENTED_ADAPTERS,
    REAL_PROVIDER_SMOKE_REQUIRED,
)
from runtime.invocation.adapters import InterfaceOnlyAdapter, OllamaAdapter, OpenAICompatibleAdapter
from runtime.models import ModelManager
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_capability_matrix_is_machine_readable():
    """Matrix is a frozen set of dataclass records, not prose."""
    assert IMPLEMENTED_ADAPTERS
    for entry in IMPLEMENTED_ADAPTERS:
        assert entry.adapter_class
        assert entry.protocol


def test_capability_matrix_matches_adapter_classes():
    """Every implemented adapter class appears in the matrix."""
    expected = {
        "OpenAICompatibleAdapter",
        "OllamaAdapter",
        "InterfaceOnlyAdapter",
    }
    actual = {entry.adapter_class for entry in IMPLEMENTED_ADAPTERS}
    assert expected == actual


def test_only_real_implementations_claimed():
    """No catalog-only provider/protocol is claimed as implemented."""
    implemented_protocols = {entry.protocol for entry in IMPLEMENTED_ADAPTERS}
    for proto in CATALOG_ONLY_PROTOCOLS:
        assert proto not in implemented_protocols
    for provider in CATALOG_ONLY_PROVIDERS:
        # Catalog providers have no dedicated adapter; only the generic
        # openai-compatible/ollama adapters can route them via config.
        assert provider not in {e.adapter_class for e in IMPLEMENTED_ADAPTERS}


def test_openai_adapter_has_real_streaming():
    entry = next(e for e in IMPLEMENTED_ADAPTERS if e.adapter_class == "OpenAICompatibleAdapter")
    assert entry.streaming is True
    assert entry.sse_parsing is True
    assert entry.non_streaming is True
    assert entry.usage_parsing is True
    assert entry.finish_reason_parsing is True


def test_ollama_adapter_has_real_streaming():
    entry = next(e for e in IMPLEMENTED_ADAPTERS if e.adapter_class == "OllamaAdapter")
    assert entry.streaming is True
    assert entry.ndjson_parsing is True
    assert entry.non_streaming is True
    assert entry.usage_parsing is True
    assert entry.finish_reason_parsing is True


def test_interface_only_adapter_is_not_claimed_as_streaming():
    entry = next(e for e in IMPLEMENTED_ADAPTERS if e.adapter_class == "InterfaceOnlyAdapter")
    assert entry.streaming is False
    assert entry.non_streaming is False


def test_configured_models_are_loadable():
    manager = ModelManager(ROOT / "config" / "models.yaml")
    for model_id in CONFIGURED_MODELS:
        model = manager.resolver.find_model(model_id)
        assert model is not None
        assert model.id == model_id


def test_real_provider_smoke_is_not_required_for_ci():
    """Deterministic CI must not depend on external provider credentials."""
    assert REAL_PROVIDER_SMOKE_REQUIRED is False


def test_adapter_protocol_attributes_are_consistent():
    """Class-level protocol attributes match the matrix protocol values."""
    adapters = {
        "OpenAICompatibleAdapter": OpenAICompatibleAdapter,
        "OllamaAdapter": OllamaAdapter,
        "InterfaceOnlyAdapter": InterfaceOnlyAdapter,
    }
    for entry in IMPLEMENTED_ADAPTERS:
        cls = adapters[entry.adapter_class]
        assert cls.protocol == entry.protocol
