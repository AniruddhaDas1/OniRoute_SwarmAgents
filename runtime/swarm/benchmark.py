"""Performance benchmarking utility for Swarm Initialization (Phase P3.A2)."""

from __future__ import annotations

import time
import tracemalloc
from typing import Any, Dict

from runtime.deployment.models import MissionDeploymentPlan

from .engine import SwarmInitializationEngine


def benchmark_swarm_initialization(
    engine: SwarmInitializationEngine,
    deployment_plan: MissionDeploymentPlan,
    iterations: int = 100,
) -> Dict[str, Any]:
    """Benchmark initialization latency, session creation speed, memory usage, and snapshot determinism."""
    tracemalloc.start()
    mem_before, _ = tracemalloc.get_traced_memory()

    t0 = time.perf_counter()
    snapshot = engine.initialize_swarm(deployment_plan)
    t1 = time.perf_counter()

    initialization_latency_ms = (t1 - t0) * 1000.0

    # Repeated initialization determinism & latency
    hashes = set()
    session_counts = []

    t_repeat_start = time.perf_counter()
    for _ in range(iterations):
        snap = engine.initialize_swarm(deployment_plan)
        hashes.add(snap.snapshot_hash)
        session_counts.append(len(snap.sessions))
    t_repeat_end = time.perf_counter()

    repeat_avg_latency_ms = ((t_repeat_end - t_repeat_start) / iterations) * 1000.0

    mem_after, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    is_deterministic = len(hashes) == 1 and all(c == session_counts[0] for c in session_counts)

    return {
        "initialization_latency_ms": round(initialization_latency_ms, 3),
        "repeat_avg_latency_ms": round(repeat_avg_latency_ms, 3),
        "iterations": iterations,
        "is_deterministic": is_deterministic,
        "unique_hash_count": len(hashes),
        "sample_snapshot_hash": snapshot.snapshot_hash,
        "memory_used_kb": round((mem_after - mem_before) / 1024.0, 2),
        "peak_memory_kb": round(mem_peak / 1024.0, 2),
        "session_count": len(snapshot.sessions),
        "wave_count": len(snapshot.wave_status),
        "execution_uuid": snapshot.execution_uuid,
    }
