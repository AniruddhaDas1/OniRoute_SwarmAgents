"""Tests for Phase P3.A4 Swarm Coordination."""

from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillRankingEngine,
    SkillBundlingEngine,
    AgentProfileBuilderEngine,
)
from runtime.deployment import MissionDeploymentPlanner
from runtime.swarm import (
    SwarmInitializationEngine,
    AutonomousExecutionEngine,
    SwarmCoordinationEngine,
    ArtifactExchange,
    SharedContextManager,
    HandoffCoordinator,
    SwarmConsensusEngine,
    RuntimeExecutionSnapshot,
    SwarmInitializationError,
    benchmark_swarm_coordination,
)


runner = CliRunner()


@pytest.fixture
def registry_and_resolver():
    root = Path.cwd()
    loader = RepositoryLoader(root)
    reg = loader.load()
    res = Resolver(reg)
    return reg, res


def create_sample_plan(
    plan_id: str = "plan-coord-004",
    mission_id: str = "msn-coord-004",
    project_goal: str = "Test Swarm Coordination Goal",
    project_type: str = "python",
    technology_stack: list[str] | None = None,
    required_disciplines: list[str] | None = None,
) -> EngineeringExecutionPlan:
    return EngineeringExecutionPlan(
        plan_id=plan_id,
        mission_id=mission_id,
        project_goal=project_goal,
        current_project_state="EXISTING_PROJECT",
        target_project_state="UPDATED_PROJECT",
        project_type=project_type,
        technology_stack=technology_stack or ["Python"],
        repository_strategy=RepositoryStrategy.FEATURE_ADDITION,
        required_deliverables=["Project Configuration"],
        required_disciplines=required_disciplines or ["Software Engineering"],
        high_level_milestones=[{"step": 1, "name": "Setup", "objective": "Setup project", "deliverables": []}],
        known_constraints=[],
        risks=[],
        missing_information=[],
        success_criteria=["Builds cleanly"],
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
    )


def execute_sample_swarm(registry, resolver, plan: EngineeringExecutionPlan):
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)
    deployment_planner = MissionDeploymentPlanner()
    swarm_init_engine = SwarmInitializationEngine()
    exec_engine = AutonomousExecutionEngine()

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)
    deployment_plan = deployment_planner.create_deployment_plan(plan, profile_report)
    init_snapshot = swarm_init_engine.initialize_swarm(deployment_plan)
    exec_snapshot, results = exec_engine.execute_swarm(init_snapshot)
    return exec_snapshot, results


def test_artifact_exchange_registration_and_delivery(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Artifact exchange test project")
    exec_snapshot, results = execute_sample_swarm(registry, resolver, plan)

    exchange = ArtifactExchange()
    records = exchange.register_artifacts_from_results(results)

    assert len(records) > 0
    assert all(r.version == "v1.0.0" for r in records)
    assert all(r.delivery_status in ("DELIVERED", "CONFIRMED") for r in records)


def test_shared_context_merging_and_versioning(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Shared context test project")
    exec_snapshot, results = execute_sample_swarm(registry, resolver, plan)

    manager = SharedContextManager()
    init_ctx = manager.create_initial_snapshot("msn-coord-test", {"env": "test"})
    merged_ctx = manager.merge_execution_outcomes(init_ctx, results)

    assert merged_ctx.version_index == 2
    assert merged_ctx.previous_snapshot_id == init_ctx.snapshot_id
    assert merged_ctx.context_data["total_tasks_completed"] == len(results)


def test_parallel_task_coordination(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Parallel task coordination project",
        technology_stack=["React", "FastAPI", "PostgreSQL", "Docker"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps", "Testing"],
    )
    exec_snapshot, results = execute_sample_swarm(registry, resolver, plan)
    coord_engine = SwarmCoordinationEngine()

    coord_snapshot, summary = coord_engine.coordinate_swarm(exec_snapshot, results)

    assert isinstance(coord_snapshot, RuntimeExecutionSnapshot)
    assert summary["coordination_latency_ms"] >= 0.0
    assert len(summary["messages"]) == len(results)
    assert len(summary["handoffs"]) > 0


def test_artifact_and_context_conflict_resolution(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Conflict resolution test project")
    exec_snapshot, results = execute_sample_swarm(registry, resolver, plan)
    coord_engine = SwarmCoordinationEngine()

    coord_snapshot, summary = coord_engine.coordinate_swarm(exec_snapshot, results, force_conflict=True)

    assert len(summary["conflicts"]) >= 1
    assert summary["conflicts"][0]["resolved"] is True
    assert summary["conflicts"][0]["resolution_strategy"] == "VERSION_BRANCH"


def test_wave_gate_consensus_evaluation(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Consensus evaluation test project")
    exec_snapshot, results = execute_sample_swarm(registry, resolver, plan)

    consensus_engine = SwarmConsensusEngine()
    csn = consensus_engine.evaluate_wave_consensus(1, "Wave 1 Review Gate", ["ap-devops-001"])

    assert csn.wave_number == 1
    assert csn.decision == "APPROVED"
    assert csn.consensus_type == "REVIEW_APPROVAL"


def test_human_approval_gate_escalation():
    consensus_engine = SwarmConsensusEngine()
    csn = consensus_engine.evaluate_wave_consensus(3, "Human Approval Gate", ["ap-security-001"], force_escalation=True)

    assert csn.decision == "ESCALATED_TO_HUMAN"
    assert csn.tie_breaker_applied is True


def test_repeated_coordination_determinism(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Deterministic coordination test project")
    exec_snapshot, results = execute_sample_swarm(registry, resolver, plan)
    coord_engine = SwarmCoordinationEngine()

    bench = benchmark_swarm_coordination(coord_engine, exec_snapshot, results, iterations=20)

    assert bench["is_deterministic"] is True
    assert bench["unique_hash_count"] == 1
    assert bench["msg_throughput_per_sec"] >= 0.0


def test_empty_snapshot_coordination_error():
    empty_snapshot = RuntimeExecutionSnapshot(
        snapshot_id="snap-empty",
        mission_id="msn-empty",
        deployment_plan_id="dep-empty",
        execution_uuid="exec-uuid-empty",
        wave_status={},
        session_map={},
        sessions=[],
        execution_cursor={"active_wave_number": 1, "execution_state": "READY"},
        execution_context={},
        budget_status={"total_budget_usd": 50.0, "spent_budget_usd": 0.0, "remaining_budget_usd": 50.0},
        retry_status={"total_retries_attempted": 0},
        checkpoint_status={"current_checkpoint_id": "chk-w1-init-empty"},
        event_bus_references={"bus_id": "bus-empty"},
        storage_references={
            "workspace_root": "/tmp",
            "sessions_root": "/tmp/sessions",
            "traces_root": "/tmp/traces",
            "logs_root": "/tmp/logs",
            "history_root": "/tmp/history",
            "reports_root": "/tmp/reports",
            "artifacts_root": "/tmp/artifacts",
        },
        workspace_references={
            "workspace_id": "ws-empty",
            "workspace_root": "/tmp",
            "engine_root": "/tmp",
            "is_engine_read_only": False,
            "project_type": "python",
        },
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
        snapshot_hash="hash-empty",
    )
    coord_engine = SwarmCoordinationEngine()

    with pytest.raises(SwarmInitializationError):
        coord_engine.coordinate_swarm(empty_snapshot, [])


def test_cli_coordinate_command():
    result = runner.invoke(app, ["coordinate", "Build React FastAPI application"])
    assert result.exit_code == 0
    assert "Swarm Coordination Complete" in result.output
    assert "Agent Messages" in result.output
    assert "Artifact Exchange" in result.output
    assert "APPROVED" in result.output


def test_cli_coordinate_json_command():
    result = runner.invoke(app, ["coordinate", "--json", "Build React FastAPI application"])
    assert result.exit_code == 0
    assert '"snapshot":' in result.output
    assert '"coordination_summary":' in result.output
    assert '"artifact_exchanges":' in result.output
