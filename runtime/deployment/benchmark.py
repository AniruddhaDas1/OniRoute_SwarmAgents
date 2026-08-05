"""Performance benchmarking utility for Mission Deployment Planner (Phase P3.A1)."""

from __future__ import annotations

import time
import tracemalloc
from typing import Any, Dict

from runtime.skills.models import AgentProfileReport
from runtime.workspace.plan import EngineeringExecutionPlan

from .planner import MissionDeploymentPlanner


def benchmark_deployment_planner(
    planner: MissionDeploymentPlanner,
    plan: EngineeringExecutionPlan,
    profile_report: AgentProfileReport,
    iterations: int = 100,
) -> Dict[str, Any]:
    """Benchmark planning latency, wave generation, validation time, memory usage, and determinism."""
    tracemalloc.start()
    mem_before, _ = tracemalloc.get_traced_memory()

    t0 = time.perf_counter()

    # Initial plan generation
    deployment_plan = planner.create_deployment_plan(plan, profile_report)
    t1 = time.perf_counter()

    planning_latency_ms = (t1 - t0) * 1000.0

    # Test repeated execution consistency & determinism
    hashes = set()
    wave_structures = []

    t_repeat_start = time.perf_counter()
    for _ in range(iterations):
        dp = planner.create_deployment_plan(plan, profile_report)
        hashes.add(dp.deployment_hash)
        wave_structures.append([w.profile_ids for w in dp.execution_waves])
    t_repeat_end = time.perf_counter()

    repeat_avg_latency_ms = ((t_repeat_end - t_repeat_start) / iterations) * 1000.0

    mem_after, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    is_deterministic = len(hashes) == 1 and all(ws == wave_structures[0] for ws in wave_structures)

    return {
        "planning_latency_ms": round(planning_latency_ms, 3),
        "repeat_avg_latency_ms": round(repeat_avg_latency_ms, 3),
        "iterations": iterations,
        "is_deterministic": is_deterministic,
        "unique_hash_count": len(hashes),
        "sample_deployment_hash": deployment_plan.deployment_hash,
        "memory_used_kb": round((mem_after - mem_before) / 1024.0, 2),
        "peak_memory_kb": round(mem_peak / 1024.0, 2),
        "wave_count": len(deployment_plan.execution_waves),
        "profile_count": len(deployment_plan.agent_profiles),
        "review_gate_count": len(deployment_plan.review_gates),
        "approval_gate_count": len(deployment_plan.approval_gates),
        "artifact_route_count": len(deployment_plan.artifact_routes),
    }
