"""E1.7.12 Freeze manifest verification."""

from __future__ import annotations

from pathlib import Path

from runtime.freeze import (
    FROZEN_CONTRACTS,
    FROZEN_MODULES,
    KNOWN_LIMITATIONS,
    ONIROUTE_VERSION,
    PROHIBITED_MODIFICATIONS,
    PROVIDER_COMPATIBILITY,
    RUNTIME_VERSION,
    CompatibilityStatus,
    ContractStatus,
)

ROOT = Path(__file__).parents[2]


def test_version_constants():
    assert ONIROUTE_VERSION == "v1.2.1"
    assert RUNTIME_VERSION == "v1.2.1-e1.7"


def test_manifest_is_deterministic():
    """Re-importing the manifest produces identical data (no mutable globals)."""
    import importlib
    import runtime.freeze.manifest as m1
    importlib.reload(m1)
    import runtime.freeze.manifest as m2
    assert m1.FROZEN_MODULES == m2.FROZEN_MODULES
    assert m1.FROZEN_CONTRACTS == m2.FROZEN_CONTRACTS
    assert m1.PROVIDER_COMPATIBILITY == m2.PROVIDER_COMPATIBILITY


def test_all_frozen_modules_exist():
    for frozen in FROZEN_MODULES:
        assert (ROOT / frozen.path).exists(), f"Missing frozen module: {frozen.path}"


def test_frozen_modules_are_frozen():
    """Frozen modules must be marked FROZEN or PUBLIC_CONTRACT."""
    for frozen in FROZEN_MODULES:
        assert frozen.status in (ContractStatus.FROZEN, ContractStatus.PUBLIC_CONTRACT)


def test_compatibility_statuses_distinct():
    """All five compatibility statuses are used appropriately."""
    statuses = {entry.status for entry in PROVIDER_COMPATIBILITY}
    assert CompatibilityStatus.SUPPORTED in statuses or CompatibilityStatus.VERIFIED in statuses
    assert CompatibilityStatus.UNSUPPORTED in statuses


def test_known_limitations_documented():
    assert len(KNOWN_LIMITATIONS) >= 4
    assert any("OpenAI-compatible" in lim for lim in KNOWN_LIMITATIONS)


def test_prohibited_modifications_documented():
    assert any("InvocationEngine" in p for p in PROHIBITED_MODIFICATIONS)
    assert any("ModelSelector" in p for p in PROHIBITED_MODIFICATIONS)
    assert any("retries" in p for p in PROHIBITED_MODIFICATIONS)
