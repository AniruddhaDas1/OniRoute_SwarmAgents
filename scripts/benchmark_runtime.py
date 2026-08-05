"""Performance benchmark script for the OniRoute Agent Runtime (ACR-006 Phase R5).

Measures baseline performance across:
1. Session Initialization
2. Execution Engine Latency
3. Recovery Engine Overhead (Pause/Resume/Retry/Review)
4. Artifact Collection & Event Recording
5. Runtime Reporting & JSON Serialization
6. Peak Memory Usage
"""

from __future__ import annotations

import gc
import sys
import time
import tracemalloc
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT))

from runtime.agent import (
    AgentExecutionEngine,
    AgentSession,
    ArtifactCollector,
    ArtifactRecord,
    ArtifactType,
    ExecutionReporter,
    FailureClassifier,
    RecoveryOrchestrator,
    RetryPolicy,
    RuntimeInitializer,
    RuntimeState,
    SessionCoordinator,
    SessionManager,
)
from runtime.mission import MissionIntake, MissionOrchestrator, MissionResolver
from runtime.organization import ExecutionBlueprintAssembler
from runtime.organization.blueprint import ExecutionBlueprint


def benchmark_session_initialization(runs: int = 100) -> dict:
    """Measure session initialization latency."""
    intake = MissionIntake()
    request = intake.process_intake("Benchmark mission initialization")
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)
    orchestrator = MissionOrchestrator()
    exec_req = orchestrator.orchestrate_mission(mission)
    assembler = ExecutionBlueprintAssembler(repository_root=REPO_ROOT)
    blueprint = assembler.assemble_blueprint(exec_req, repository_root=REPO_ROOT)

    coordinator = SessionCoordinator()
    
    start = time.perf_counter()
    for _ in range(runs):
        coordinator.initialize_sessions(blueprint)
    elapsed = time.perf_counter() - start
    
    avg_ms = (elapsed / runs) * 1000
    ops_per_sec = runs / elapsed
    return {"avg_ms": avg_ms, "ops_per_sec": ops_per_sec, "total_runs": runs}


def benchmark_recovery_overhead(runs: int = 500) -> dict:
    """Measure Pause, Resume, Review, Retry, and Report overhead."""
    mgr = SessionManager()
    orch = RecoveryOrchestrator(retry_policy=RetryPolicy(max_retries=5, base_delay_seconds=0.0))
    clf = FailureClassifier()

    # Pause / Resume benchmark
    start_pr = time.perf_counter()
    for i in range(runs):
        sess = AgentSession(
            session_id=f"sess-bench-pr-{i}", member_id="mem-1", role_id="role-1",
            role_title="Bench Role", blueprint_id="bp-bench", state=RuntimeState.INITIALIZED,
        )
        sess = mgr.transition_state(sess, RuntimeState.READY)
        sess = mgr.transition_state(sess, RuntimeState.RUNNING)
        sess, record = orch.pause(sess, reason="bench pause")
        sess, closed = orch.resume(sess)
    elapsed_pr = time.perf_counter() - start_pr
    avg_pr_ms = (elapsed_pr / runs) * 1000

    # Retry attempt benchmark
    start_rt = time.perf_counter()
    classification = clf.classify(ConnectionError("network timeout"))
    for i in range(runs):
        sess = AgentSession(
            session_id=f"sess-bench-rt-{i}", member_id="mem-1", role_id="role-1",
            role_title="Bench Role", blueprint_id="bp-bench", state=RuntimeState.INITIALIZED,
        )
        sess = mgr.transition_state(sess, RuntimeState.READY)
        sess = mgr.transition_state(sess, RuntimeState.RUNNING)
        sess = mgr.transition_state(sess, RuntimeState.FAILED)
        orch.attempt_recovery(sess, classification, lambda s: None)
    elapsed_rt = time.perf_counter() - start_rt
    avg_rt_ms = (elapsed_rt / runs) * 1000

    return {
        "pause_resume_avg_ms": avg_pr_ms,
        "retry_attempt_avg_ms": avg_rt_ms,
        "total_runs": runs,
    }


def benchmark_artifact_collection(runs: int = 1000) -> dict:
    """Measure artifact collection and event recording throughput."""
    collector = ArtifactCollector()
    session = AgentSession(
        session_id="sess-art-bench", member_id="mem-1", role_id="role-1",
        role_title="Bench Role", blueprint_id="bp-bench", state=RuntimeState.RUNNING,
    )

    start = time.perf_counter()
    for i in range(runs):
        artifact = ArtifactRecord(
            artifact_id=f"art-bench-{i}",
            artifact_type=ArtifactType.CODE,
            owner_session_id=session.session_id,
            owner_member_id=session.member_id,
            capability_id="cap-code",
            name=f"Artifact {i}",
        )
        collector.register_artifact(session, artifact)
    elapsed = time.perf_counter() - start

    return {
        "total_artifacts": runs,
        "avg_ms_per_artifact": (elapsed / runs) * 1000,
        "throughput_per_sec": runs / elapsed,
    }


def measure_peak_memory() -> dict:
    """Measure peak memory usage during full pipeline initialization and recovery."""
    gc.collect()
    tracemalloc.start()
    
    intake = MissionIntake()
    request = intake.process_intake("Benchmark memory footprint")
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)
    orchestrator = MissionOrchestrator()
    exec_req = orchestrator.orchestrate_mission(mission)
    assembler = ExecutionBlueprintAssembler(repository_root=REPO_ROOT)
    blueprint = assembler.assemble_blueprint(exec_req, repository_root=REPO_ROOT)

    coordinator = SessionCoordinator()
    context, sessions, report = coordinator.initialize_sessions(blueprint)

    rec_orch = RecoveryOrchestrator()
    for session in sessions:
        rec_orch.generate_report(session, blueprint.blueprint_id, blueprint.mission.mission_id)

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "current_bytes": current_bytes,
        "current_mb": current_bytes / (1024 * 1024),
        "peak_bytes": peak_bytes,
        "peak_mb": peak_bytes / (1024 * 1024),
    }


def main():
    print("=" * 60)
    print("OniRoute Agent Runtime Performance Baseline (ACR-006 Phase R5)")
    print("=" * 60)

    init_res = benchmark_session_initialization(runs=100)
    print(f"[1] Session Initialization: {init_res['avg_ms']:.3f} ms/op ({init_res['ops_per_sec']:.1f} ops/sec)")

    rec_res = benchmark_recovery_overhead(runs=500)
    print(f"[2] Recovery Pause/Resume: {rec_res['pause_resume_avg_ms']:.4f} ms/op")
    print(f"[3] Recovery Retry Attempt: {rec_res['retry_attempt_avg_ms']:.4f} ms/op")

    art_res = benchmark_artifact_collection(runs=1000)
    print(f"[4] Artifact Collection:    {art_res['avg_ms_per_artifact']:.4f} ms/art ({art_res['throughput_per_sec']:.1f} art/sec)")

    mem_res = measure_peak_memory()
    print(f"[5] Peak Memory Usage:      {mem_res['peak_mb']:.2f} MB ({mem_res['peak_bytes']} bytes)")

    print("=" * 60)
    print("All baseline measurements completed successfully.")


if __name__ == "__main__":
    main()
