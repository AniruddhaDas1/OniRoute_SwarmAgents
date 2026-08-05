"""Autonomous Swarm Certification Engine for OniRoute (Phase P3.A5).

Audits and certifies the complete Autonomous Swarm pipeline end-to-end.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

from runtime.deployment import MissionDeploymentPlanner
from runtime.intent import IntentAnalyzer
from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.skills import AgentProfileBuilderEngine, SkillBundlingEngine, SkillDiscoveryEngine, SkillRankingEngine
from runtime.workspace import EngineeringPlanGenerator, RepositoryIntelligence, WorkspaceIntelligence

from .autonomous_engine import AutonomousExecutionEngine
from .benchmark import benchmark_swarm_initialization
from .benchmark_coordination import benchmark_swarm_coordination
from .benchmark_execution import benchmark_autonomous_execution
from .coordination_engine import SwarmCoordinationEngine
from .engine import SwarmInitializationEngine
from .freeze import AUTONOMOUS_SWARM_FROZEN, SWARM_FREEZE_MANIFEST, SWARM_SUBSYSTEM_STATUS, SWARM_SUBSYSTEM_VERSION


class AutonomousSwarmCertificationEngine:
    """End-to-end certification and verification engine for the Autonomous Swarm subsystem."""

    def certify_subsystem(self, repository_root: Path | None = None) -> Dict[str, Any]:
        """Perform end-to-end audit and certify the Autonomous Swarm subsystem."""
        root = repository_root or Path.cwd()
        t0 = time.perf_counter()

        # 1. Load Repository and Resolver
        loader = RepositoryLoader(root)
        registry = loader.load()
        resolver = Resolver(registry)

        # 2. Planning (P1/P2 pre-requisites)
        intent_report = IntentAnalyzer().analyze("Build a React FastAPI web application", explicit_workspace=None)
        ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=root)
        repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
        plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

        sel_rep = SkillDiscoveryEngine(registry, resolver).discover_skills(plan)
        ranked_rep = SkillRankingEngine(registry, resolver).rank_skills(sel_rep, plan)
        bundle_rep = SkillBundlingEngine(registry, resolver).bundle_skills(ranked_rep, plan, sel_rep)
        profile_report = AgentProfileBuilderEngine(registry, resolver).build_profiles(bundle_rep, plan)

        # 3. Phase P3.A1 — Mission Deployment Planner
        t_p3a1_0 = time.perf_counter()
        dep_planner = MissionDeploymentPlanner()
        dep_plan = dep_planner.create_deployment_plan(plan, profile_report)
        t_p3a1_1 = time.perf_counter()
        p3a1_latency_ms = (t_p3a1_1 - t_p3a1_0) * 1000.0

        # 4. Phase P3.A2 — Swarm Initialization
        t_p3a2_0 = time.perf_counter()
        init_engine = SwarmInitializationEngine()
        init_snapshot = init_engine.initialize_swarm(dep_plan, repository_root=root)
        t_p3a2_1 = time.perf_counter()
        p3a2_latency_ms = (t_p3a2_1 - t_p3a2_0) * 1000.0

        # 5. Phase P3.A3 — Autonomous Execution
        t_p3a3_0 = time.perf_counter()
        exec_engine = AutonomousExecutionEngine()
        exec_snapshot, results = exec_engine.execute_swarm(init_snapshot, repository_root=root)
        t_p3a3_1 = time.perf_counter()
        p3a3_latency_ms = (t_p3a3_1 - t_p3a3_0) * 1000.0

        # 6. Phase P3.A4 — Swarm Coordination
        t_p3a4_0 = time.perf_counter()
        coord_engine = SwarmCoordinationEngine()
        coord_snapshot, summary = coord_engine.coordinate_swarm(exec_snapshot, results, repository_root=root)
        t_p3a4_1 = time.perf_counter()
        p3a4_latency_ms = (t_p3a4_1 - t_p3a4_0) * 1000.0

        t1 = time.perf_counter()
        total_pipeline_latency_ms = (t1 - t0) * 1000.0

        # 7. Benchmarks
        init_bench = benchmark_swarm_initialization(init_engine, dep_plan, iterations=10)
        exec_bench = benchmark_autonomous_execution(exec_engine, init_snapshot, iterations=10)
        coord_bench = benchmark_swarm_coordination(coord_engine, exec_snapshot, results, iterations=10)

        # 8. Pipeline Invariant Checks
        pipeline_valid = (
            dep_plan.deployment_hash != ""
            and init_snapshot.snapshot_hash != ""
            and exec_snapshot.execution_cursor.execution_state == "COMPLETED"
            and coord_snapshot.snapshot_hash != ""
            and init_bench["is_deterministic"]
            and exec_bench["is_deterministic"]
            and coord_bench["is_deterministic"]
        )

        return {
            "certified": pipeline_valid and AUTONOMOUS_SWARM_FROZEN,
            "status": SWARM_SUBSYSTEM_STATUS,
            "version": SWARM_SUBSYSTEM_VERSION,
            "manifest": SWARM_FREEZE_MANIFEST,
            "latencies_ms": {
                "deployment_planning": round(p3a1_latency_ms, 3),
                "initialization": round(p3a2_latency_ms, 3),
                "execution": round(p3a3_latency_ms, 3),
                "coordination": round(p3a4_latency_ms, 3),
                "total_end_to_end": round(total_pipeline_latency_ms, 3),
            },
            "metrics": {
                "total_sessions": len(coord_snapshot.sessions),
                "total_tasks_executed": len(results),
                "total_tokens_consumed": sum(r.consumed_tokens for r in results),
                "total_cost_usd": sum(r.cost_usd for r in results),
                "total_artifacts_exchanged": len(summary["artifact_exchanges"]),
                "total_messages_dispatched": len(summary["messages"]),
                "total_handoffs_completed": len(summary["handoffs"]),
                "total_consensus_decisions": len(summary["consensus"]),
            },
            "determinism": {
                "initialization_deterministic": init_bench["is_deterministic"],
                "execution_deterministic": exec_bench["is_deterministic"],
                "coordination_deterministic": coord_bench["is_deterministic"],
            },
        }
