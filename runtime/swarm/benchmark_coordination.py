"""Performance benchmarking utility for Swarm Coordination (Phase P3.A4)."""

from __future__ import annotations

import time
import tracemalloc
from typing import Any, Dict, List

from .coordination_engine import SwarmCoordinationEngine
from .models import RuntimeExecutionSnapshot
from .result import SwarmExecutionResult


def benchmark_swarm_coordination(
    engine: SwarmCoordinationEngine,
    snapshot: RuntimeExecutionSnapshot,
    results: List[SwarmExecutionResult],
    iterations: int = 10,
) -> Dict[str, Any]:
    """Benchmark message throughput, artifact exchange throughput, context sync, latency, and determinism."""
    tracemalloc.start()
    mem_before, _ = tracemalloc.get_traced_memory()

    t0 = time.perf_counter()
    coord_snapshot, summary = engine.coordinate_swarm(snapshot, results)
    t1 = time.perf_counter()

    coordination_latency_ms = (t1 - t0) * 1000.0

    msg_count = len(summary["messages"])
    art_count = len(summary["artifact_exchanges"])
    msg_throughput = (msg_count / (t1 - t0)) if (t1 - t0) > 0 else 0.0
    art_throughput = (art_count / (t1 - t0)) if (t1 - t0) > 0 else 0.0

    hashes = set()
    t_repeat_start = time.perf_counter()
    for _ in range(iterations):
        snap, _ = engine.coordinate_swarm(snapshot, results)
        hashes.add(snap.snapshot_hash)
    t_repeat_end = time.perf_counter()

    repeat_avg_latency_ms = ((t_repeat_end - t_repeat_start) / iterations) * 1000.0

    mem_after, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    is_deterministic = len(hashes) == 1

    return {
        "coordination_latency_ms": round(coordination_latency_ms, 3),
        "repeat_avg_latency_ms": round(repeat_avg_latency_ms, 3),
        "iterations": iterations,
        "is_deterministic": is_deterministic,
        "unique_hash_count": len(hashes),
        "sample_snapshot_hash": coord_snapshot.snapshot_hash,
        "message_count": msg_count,
        "artifact_exchange_count": art_count,
        "handoff_count": len(summary["handoffs"]),
        "consensus_count": len(summary["consensus"]),
        "msg_throughput_per_sec": round(msg_throughput, 2),
        "art_throughput_per_sec": round(art_throughput, 2),
        "memory_used_kb": round((mem_after - mem_before) / 1024.0, 2),
        "peak_memory_kb": round(mem_peak / 1024.0, 2),
    }
