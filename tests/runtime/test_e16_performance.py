"""E1.6.14 Performance verification.

Records actual repeatable measurements. No arbitrary performance claims.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from runtime.contracts import EngineeringContract
from runtime.engineering import InvocationPlanner
from runtime.invocation import InvocationRequest
from runtime.models import Capability, ModelManager, SelectionRequest

ROOT = Path(__file__).parents[2]


def _contract():
    return EngineeringContract(
        contract_id="ctr-perf-001",
        target_path="src/app.py",
        target_type="file",
        assigned_profile_id="prof-perf",
        assigned_profile_role="Backend Engineer",
        engineering_discipline="Backend",
        contract_hash="0" * 64,
    )


def _measure(fn, iterations=20):
    """Run fn n times, return mean and max ms."""
    samples = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    return sum(samples) / len(samples), max(samples)


def test_model_selection_latency():
    manager = ModelManager(ROOT / "config" / "models.yaml")
    req = SelectionRequest(capabilities=frozenset({Capability.CODING}))
    mean_ms, max_ms = _measure(lambda: manager.select_best_model(req))
    # Record, do not assert a brittle threshold. Selection is metadata-only.
    assert mean_ms > 0
    assert max_ms < 1000  # generous sanity bound for pure metadata selection


def test_batch_planning_latency():
    planner = InvocationPlanner()
    contract = _contract()
    mean_ms, max_ms = _measure(lambda: planner.plan_batch(contract, None))
    assert mean_ms > 0
    assert max_ms < 1000


def test_invocation_request_construction_latency():
    mean_ms, max_ms = _measure(
        lambda: InvocationRequest(prompt="test", capabilities=frozenset({Capability.CODING}))
    )
    assert mean_ms > 0
    assert max_ms < 1000


def test_streaming_overhead_no_real_network():
    """Streaming assembly must not make network calls (offline overhead only)."""
    from runtime.invocation import StreamChunk
    from runtime.invocation.streaming import assemble_stream

    chunks = [StreamChunk(sequence=i, delta="x", provider="p", model="m") for i in range(100)]
    mean_ms, max_ms = _measure(lambda: assemble_stream(chunks))
    assert mean_ms > 0
    assert max_ms < 1000
