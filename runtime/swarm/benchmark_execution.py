"""Performance benchmarking utility for Autonomous Execution (Phase P3.A3)."""

from __future__ import annotations

import time
import tracemalloc
from typing import Any, Dict

from .autonomous_engine import AutonomousExecutionEngine
from .models import RuntimeExecutionSnapshot


def benchmark_autonomous_execution(
    engine: AutonomousExecutionEngine,
    snapshot: RuntimeExecutionSnapshot,
    iterations: int = 10,
) -> Dict[str, Any]:
    """Benchmark execution latency, token throughput, artifact creation rate, memory, and determinism."""
    tracemalloc.start()
    mem_before, _ = tracemalloc.get_traced_memory()

    t0 = time.perf_counter()
    exec_snapshot, results = engine.execute_swarm(snapshot)
    t1 = time.perf_counter()

    execution_latency_ms = (t1 - t0) * 1000.0

    total_tokens = sum(r.consumed_tokens for r in results)
    total_artifacts = sum(len(r.produced_artifacts) for r in results)
    tokens_per_sec = (total_tokens / (t1 - t0)) if (t1 - t0) > 0 else 0.0
    artifacts_per_sec = (total_artifacts / (t1 - t0)) if (t1 - t0) > 0 else 0.0

    hashes = set()
    t_repeat_start = time.perf_counter()
    for _ in range(iterations):
        snap, res = engine.execute_swarm(snapshot)
        hashes.add(snap.snapshot_hash)
    t_repeat_end = time.perf_counter()

    repeat_avg_latency_ms = ((t_repeat_end - t_repeat_start) / iterations) * 1000.0

    mem_after, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    is_deterministic = len(hashes) == 1

    return {
        "execution_latency_ms": round(execution_latency_ms, 3),
        "repeat_avg_latency_ms": round(repeat_avg_latency_ms, 3),
        "iterations": iterations,
        "is_deterministic": is_deterministic,
        "unique_hash_count": len(hashes),
        "sample_snapshot_hash": exec_snapshot.snapshot_hash,
        "total_tokens": total_tokens,
        "total_artifacts": total_artifacts,
        "tokens_per_sec": round(tokens_per_sec, 2),
        "artifacts_per_sec": round(artifacts_per_sec, 2),
        "memory_used_kb": round((mem_after - mem_before) / 1024.0, 2),
        "peak_memory_kb": round(mem_peak / 1024.0, 2),
        "task_count": len(results),
        "execution_state": exec_snapshot.execution_cursor.execution_state,
    }
