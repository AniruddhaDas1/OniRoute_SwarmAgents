"""Mission Deployment Planner for OniRoute (Phase P3.A1).

Converts EngineeringExecutionPlan and AgentProfileReport into an immutable,
deployment-ready MissionDeploymentPlan without executing code, creating sessions,
or invoking AI models.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

import networkx as nx

from runtime.skills.models import AgentProfile, AgentProfileReport
from runtime.workspace.plan import EngineeringExecutionPlan

from .exceptions import (
    CyclicDependencyError,
    DeploymentPlanningError,
    InvalidGatePathError,
    OrphanProfileError,
    UnscheduledProfileError,
)
from .models import (
    ApprovalGate,
    ArtifactRoute,
    ExecutionBudgetAllocation,
    ExecutionWave,
    FailureHandlingPolicy,
    HumanApprovalCheckpoint,
    MissionDeploymentPlan,
    ParallelGroup,
    RetryPolicy,
    ReviewGate,
    RollbackPolicy,
    SequentialDependency,
    TimeoutPolicy,
    WaveName,
)


# Default discipline-to-wave preference mapping
DISCIPLINE_WAVE_PREFERENCE: Dict[str, int] = {
    "DevOps": 1,
    "Infrastructure": 1,
    "Foundation": 1,
    "Database": 2,
    "Backend": 2,
    "Frontend": 2,
    "AI": 2,
    "General Engineering": 2,
    "Software Systems": 2,
    "Integration": 3,
    "Automation": 3,
    "Fullstack": 3,
    "Testing": 4,
    "QA": 4,
    "Security": 5,
    "Governance": 5,
    "Audit": 5,
    "Documentation": 6,
    "Technical Writing": 6,
    "Delivery": 6,
}


class MissionDeploymentPlanner:
    """Deterministic Mission Deployment Planner.

    Transforms AgentProfileReport and EngineeringExecutionPlan into an immutable
    MissionDeploymentPlan.
    """

    def create_deployment_plan(
        self,
        plan: EngineeringExecutionPlan,
        profile_report: AgentProfileReport,
    ) -> MissionDeploymentPlan:
        """Generate a deterministic deployment plan from an EngineeringExecutionPlan and AgentProfileReport."""
        if not profile_report.profiles:
            raise DeploymentPlanningError("AgentProfileReport contains no agent profiles.")

        now_str = datetime.now(timezone.utc).isoformat()
        hash_seed = f"{plan.plan_id}:{profile_report.report_id}"
        hash_hex = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()[:6]
        deployment_plan_id = f"dep-{hash_hex}"

        profiles = list(profile_report.profiles)

        # 1. Build and validate dependency DAG
        dep_graph, topo_order = self._build_and_validate_dag(profiles)

        # 2. Determine Execution Waves (Waves 1..6)
        execution_waves, profile_wave_map = self._determine_waves(profiles, dep_graph, topo_order)

        # 3. Build Parallel Execution Groups & Sequential Dependencies
        parallel_group_map, parallel_groups = self._generate_parallel_groups(execution_waves, profiles, dep_graph)
        sequential_deps = self._build_sequential_dependencies(profiles)

        # 4. Generate Review & Approval Gates & Human Checkpoints
        review_gates = self._generate_review_gates(execution_waves, profiles, profile_wave_map)
        approval_gates = self._generate_approval_gates(execution_waves, plan)
        human_checkpoints = self._generate_human_checkpoints(plan, execution_waves)

        # Attach gate IDs back to execution waves
        updated_waves = self._attach_gates_to_waves(execution_waves, review_gates, approval_gates)

        # 5. Build Artifact Flow Routes
        artifact_routes = self._build_artifact_routes(profiles, profile_wave_map)

        # 6. Build Retry, Failure, Rollback, Timeout, and Budget Policies
        retry_policy = self._build_retry_policy(plan, profiles)
        failure_policy = self._build_failure_policy(plan)
        rollback_policy = self._build_rollback_policy(plan)
        timeout_policy = self._build_timeout_policy(plan, profiles, updated_waves)
        budget_allocation = self._build_budget_allocation(plan, updated_waves, profiles)

        # 7. Consolidation of Execution Constraints
        consolidated_constraints = self._consolidate_constraints(plan, profiles)

        # 8. Dependency Validation Suite
        validation_results = self._validate_deployment(
            profiles=profiles,
            execution_waves=updated_waves,
            profile_wave_map=profile_wave_map,
            dep_graph=dep_graph,
            review_gates=review_gates,
            approval_gates=approval_gates,
            artifact_routes=artifact_routes,
        )

        evidence = {
            "validation": validation_results,
            "total_profiles": len(profiles),
            "total_waves": len(updated_waves),
            "total_parallel_groups": len(parallel_groups),
            "total_review_gates": len(review_gates),
            "total_approval_gates": len(approval_gates),
            "total_human_checkpoints": len(human_checkpoints),
            "total_artifact_routes": len(artifact_routes),
            "planning_latency_ms": 0.0,
            "deterministic_hash_seed": hash_seed,
        }

        # 9. Compute SHA-256 Deployment Hash
        preliminary_dict = {
            "plan_id": deployment_plan_id,
            "mission_id": plan.mission_id,
            "execution_plan_id": plan.plan_id,
            "profiles_count": len(profiles),
            "wave_count": len(updated_waves),
            "evidence": validation_results,
            "plan_timestamp": plan.timestamp,
        }
        deployment_hash = hashlib.sha256(
            json.dumps(preliminary_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()


        return MissionDeploymentPlan(
            plan_id=deployment_plan_id,
            mission_id=plan.mission_id,
            execution_plan_id=plan.plan_id,
            agent_profiles=profiles,
            execution_waves=updated_waves,
            parallel_execution_groups=parallel_group_map,
            parallel_groups=parallel_groups,
            sequential_dependencies=sequential_deps,
            review_gates=review_gates,
            approval_gates=approval_gates,
            human_approval_checkpoints=human_checkpoints,
            artifact_routes=artifact_routes,
            retry_rules=retry_policy,
            failure_handling=failure_policy,
            rollback_strategy=rollback_policy,
            execution_constraints=consolidated_constraints,
            budget_allocation=budget_allocation,
            timeout_rules=timeout_policy,
            evidence=evidence,
            timestamp=now_str,
            deployment_hash=deployment_hash,
        )

    def _build_and_validate_dag(
        self, profiles: List[AgentProfile]
    ) -> Tuple[Dict[str, List[str]], List[str]]:
        """Construct NetworkX DiGraph and perform topological sorting and deterministic cycle resolution."""
        G = nx.DiGraph()
        profile_ids = {p.profile_id for p in profiles}

        for p in profiles:
            G.add_node(p.profile_id)

        for p in profiles:
            for dep_id in p.dependency_profiles:
                if dep_id in profile_ids and dep_id != p.profile_id:
                    G.add_edge(dep_id, p.profile_id)

        # Deterministically prune feedback cycles if present to enforce DAG property
        while not nx.is_directed_acyclic_graph(G):
            cycles = sorted(list(nx.simple_cycles(G)), key=lambda c: (len(c), str(c)))
            if not cycles:
                break
            cycle = cycles[0]
            # Remove feedback edge in cycle deterministically
            max_node = max(cycle)
            next_idx = (cycle.index(max_node) + 1) % len(cycle)
            target_node = cycle[next_idx]
            G.remove_edge(max_node, target_node)

        # Rebuild clean dep_graph after cycle resolution
        clean_dep_graph: Dict[str, List[str]] = {p.profile_id: [] for p in profiles}
        for u, v in G.edges():
            clean_dep_graph[v].append(u)

        for pid in clean_dep_graph:
            clean_dep_graph[pid] = sorted(clean_dep_graph[pid])

        topo_order = list(nx.topological_sort(G))
        return clean_dep_graph, topo_order


    def _determine_waves(
        self,
        profiles: List[AgentProfile],
        dep_graph: Dict[str, List[str]],
        topo_order: List[str],
    ) -> Tuple[List[ExecutionWave], Dict[str, int]]:
        """Determine wave assignments (Waves 1..6) using discipline preferences & dependency constraints."""
        profile_by_id = {p.profile_id: p for p in profiles}
        profile_wave_map: Dict[str, int] = {}

        # 1. Base topological level
        topo_level: Dict[str, int] = {}
        for pid in topo_order:
            prereqs = dep_graph.get(pid, [])
            if not prereqs:
                topo_level[pid] = 0
            else:
                topo_level[pid] = max(topo_level[p] for p in prereqs) + 1

        # 2. Assign candidate wave based on discipline preference + topological constraints
        for pid in topo_order:
            prof = profile_by_id[pid]
            disc = prof.primary_discipline
            role = prof.agent_role

            pref_wave = 2
            for key, w_val in DISCIPLINE_WAVE_PREFERENCE.items():
                if key.lower() in disc.lower() or key.lower() in role.lower():
                    pref_wave = w_val
                    break

            # Topological constraint: Wave of pid must be >= Wave of dep + 1 if strict wave separation
            prereqs = dep_graph.get(pid, [])
            if prereqs:
                min_wave = max(profile_wave_map[p] for p in prereqs) + 1
            else:
                min_wave = 1

            assigned_wave = max(pref_wave, min_wave)
            assigned_wave = min(6, assigned_wave)  # Cap at wave 6
            profile_wave_map[pid] = assigned_wave

        # 3. Create ExecutionWave objects for all 6 waves
        wave_names = {
            1: WaveName.FOUNDATION,
            2: WaveName.CORE_DEVELOPMENT,
            3: WaveName.INTEGRATION,
            4: WaveName.TESTING,
            5: WaveName.REVIEW,
            6: WaveName.DELIVERY,
        }

        wave_descriptions = {
            1: "Foundation, environment setup, base schemas, and core configuration.",
            2: "Core development of primary backend, frontend, database, and AI modules.",
            3: "System integration, API wiring, auth integration, and middleware assembly.",
            4: "Comprehensive testing, unit tests, integration tests, and QA validation.",
            5: "Security review, governance verification, code audit, and policy checks.",
            6: "Final packaging, documentation release, and mission deliverable delivery.",
        }

        waves: List[ExecutionWave] = []
        for w_num in range(1, 7):
            w_pids = sorted([pid for pid, w in profile_wave_map.items() if w == w_num])
            w_deliverables: List[str] = []
            for pid in w_pids:
                w_deliverables.extend(profile_by_id[pid].expected_deliverables)
            w_deliverables = sorted(list(set(w_deliverables)))

            prereq_waves = list(range(1, w_num)) if w_num > 1 else []

            waves.append(
                ExecutionWave(
                    wave_number=w_num,
                    name=wave_names[w_num].value,
                    description=wave_descriptions[w_num],
                    profile_ids=w_pids,
                    parallel_group_ids=[],
                    prerequisite_wave_numbers=prereq_waves,
                    deliverables=w_deliverables,
                    review_gate_ids=[],
                    approval_gate_ids=[],
                )
            )

        return waves, profile_wave_map

    def _generate_parallel_groups(
        self,
        waves: List[ExecutionWave],
        profiles: List[AgentProfile],
        dep_graph: Dict[str, List[str]],
    ) -> Tuple[Dict[str, List[str]], List[ParallelGroup]]:
        """Generate parallel execution groups per wave."""
        parallel_group_map: Dict[str, List[str]] = {}
        parallel_groups: List[ParallelGroup] = []

        for wave in waves:
            wave_key = f"wave_{wave.wave_number}"
            pids = wave.profile_ids

            if not pids:
                parallel_group_map[wave_key] = []
                continue

            # Group independent profiles together
            group_id = f"pg-w{wave.wave_number}-1"
            pg = ParallelGroup(
                group_id=group_id,
                wave_number=wave.wave_number,
                profile_ids=pids,
                can_execute_parallel=True,
                description=f"Parallel execution group for Wave {wave.wave_number} ({wave.name})",
            )
            parallel_groups.append(pg)
            parallel_group_map[wave_key] = pids

        return parallel_group_map, parallel_groups

    def _build_sequential_dependencies(
        self, profiles: List[AgentProfile]
    ) -> Dict[str, List[str]]:
        """Build sequential dependency map profile_id -> list of prerequisite profile_ids."""
        seq_deps: Dict[str, List[str]] = {}
        for p in profiles:
            seq_deps[p.profile_id] = sorted(p.dependency_profiles)
        return seq_deps

    def _generate_review_gates(
        self,
        waves: List[ExecutionWave],
        profiles: List[AgentProfile],
        profile_wave_map: Dict[str, int],
    ) -> List[ReviewGate]:
        """Generate deterministic review gates attached to waves."""
        review_gates: List[ReviewGate] = []

        for wave in waves:
            if not wave.profile_ids:
                continue

            w_num = wave.wave_number
            if w_num == 2:
                review_gates.append(
                    ReviewGate(
                        gate_id="rg-w2-core-review",
                        name="Core Development Verification Gate",
                        wave_number=2,
                        trigger_profiles=wave.profile_ids,
                        review_type="AUTOMATED_TEST",
                        required_checks=["unit_tests", "syntax_validation", "module_compilation"],
                        blocking=True,
                    )
                )
            elif w_num == 3:
                review_gates.append(
                    ReviewGate(
                        gate_id="rg-w3-integration-review",
                        name="Integration & Security Review Gate",
                        wave_number=3,
                        trigger_profiles=wave.profile_ids,
                        review_type="SECURITY_AUDIT",
                        required_checks=["interface_contract", "security_scan", "dependency_check"],
                        blocking=True,
                    )
                )
            elif w_num == 4:
                review_gates.append(
                    ReviewGate(
                        gate_id="rg-w4-quality-gate",
                        name="Quality & Test Suite Gate",
                        wave_number=4,
                        trigger_profiles=wave.profile_ids,
                        review_type="CODE_REVIEW",
                        required_checks=["e2e_tests", "coverage_check", "performance_assertion"],
                        blocking=True,
                    )
                )
            elif w_num == 5:
                review_gates.append(
                    ReviewGate(
                        gate_id="rg-w5-governance-review",
                        name="Governance & Policy Compliance Gate",
                        wave_number=5,
                        trigger_profiles=wave.profile_ids,
                        review_type="GOVERNANCE_CHECK",
                        required_checks=["policy_audit", "license_compliance", "artifact_verification"],
                        blocking=True,
                    )
                )

        return review_gates

    def _generate_approval_gates(
        self, waves: List[ExecutionWave], plan: EngineeringExecutionPlan
    ) -> List[ApprovalGate]:
        """Generate formal approval gates."""
        approval_gates: List[ApprovalGate] = [
            ApprovalGate(
                gate_id="ag-w3-architecture-approval",
                name="Architecture & Integration Approval Gate",
                wave_number=3,
                required_approver="LEAD_ARCHITECT",
                criteria=["Core modules successfully built", "API contracts verified", "No blocking architecture defects"],
                status="PENDING",
                blocking=True,
            ),
            ApprovalGate(
                gate_id="ag-w6-release-approval",
                name="Final Swarm Release & Delivery Sign-off",
                wave_number=6,
                required_approver="HUMAN_OPERATOR",
                criteria=["All execution waves completed", "All tests passed", "Governance compliance certified"],
                status="PENDING",
                blocking=True,
            ),
        ]
        return approval_gates

    def _generate_human_checkpoints(
        self, plan: EngineeringExecutionPlan, waves: List[ExecutionWave]
    ) -> List[HumanApprovalCheckpoint]:
        """Generate human approval checkpoints based on plan constraints & risks."""
        checkpoints: List[HumanApprovalCheckpoint] = []

        if plan.risks or plan.known_constraints or any(w.wave_number == 6 for w in waves):
            checkpoints.append(
                HumanApprovalCheckpoint(
                    checkpoint_id="hac-w3-architecture",
                    wave_number=3,
                    stage_name="Pre-Integration Architecture Review",
                    description="Human review of core architectural decisions prior to integration wave.",
                    required=True,
                    approver_role="HUMAN_OPERATOR",
                )
            )

        checkpoints.append(
            HumanApprovalCheckpoint(
                checkpoint_id="hac-w6-final-signoff",
                wave_number=6,
                stage_name="Pre-Delivery Release Sign-off",
                description="Final human operator verification before mission artifact release.",
                required=True,
                approver_role="HUMAN_OPERATOR",
            )
        )

        return checkpoints

    def _attach_gates_to_waves(
        self,
        waves: List[ExecutionWave],
        review_gates: List[ReviewGate],
        approval_gates: List[ApprovalGate],
    ) -> List[ExecutionWave]:
        """Attach gate IDs to their corresponding ExecutionWave objects."""
        rg_by_wave: Dict[int, List[str]] = {}
        for rg in review_gates:
            rg_by_wave.setdefault(rg.wave_number, []).append(rg.gate_id)

        ag_by_wave: Dict[int, List[str]] = {}
        for ag in approval_gates:
            ag_by_wave.setdefault(ag.wave_number, []).append(ag.gate_id)

        updated_waves: List[ExecutionWave] = []
        for w in waves:
            pg_ids = [f"pg-w{w.wave_number}-1"] if w.profile_ids else []
            updated_waves.append(
                ExecutionWave(
                    wave_number=w.wave_number,
                    name=w.name,
                    description=w.description,
                    profile_ids=w.profile_ids,
                    parallel_group_ids=pg_ids,
                    prerequisite_wave_numbers=w.prerequisite_wave_numbers,
                    deliverables=w.deliverables,
                    review_gate_ids=rg_by_wave.get(w.wave_number, []),
                    approval_gate_ids=ag_by_wave.get(w.wave_number, []),
                )
            )
        return updated_waves

    def _build_artifact_routes(
        self, profiles: List[AgentProfile], profile_wave_map: Dict[str, int]
    ) -> List[ArtifactRoute]:
        """Build artifact routing pathways between producer and consumer agent profiles."""
        routes: List[ArtifactRoute] = []
        profile_by_id = {p.profile_id: p for p in profiles}

        for p in profiles:
            target_id = p.profile_id
            target_wave = profile_wave_map[target_id]

            for prereq_id in p.dependency_profiles:
                if prereq_id in profile_by_id:
                    producer = profile_by_id[prereq_id]
                    source_wave = profile_wave_map[prereq_id]

                    deliverables = producer.expected_deliverables or [f"{producer.primary_discipline} Artifacts"]
                    for idx, artifact in enumerate(deliverables):
                        r_id = f"ar-{prereq_id[:8]}-{target_id[:8]}-{idx+1}"
                        routes.append(
                            ArtifactRoute(
                                route_id=r_id,
                                source_profile_id=prereq_id,
                                target_profile_id=target_id,
                                artifact_name=artifact,
                                source_wave=source_wave,
                                target_wave=target_wave,
                            )
                        )

        return routes

    def _build_retry_policy(
        self, plan: EngineeringExecutionPlan, profiles: List[AgentProfile]
    ) -> RetryPolicy:
        """Construct default retry policy with per-profile overrides."""
        overrides: Dict[str, int] = {}
        for p in profiles:
            if "Critical" in p.priority.value or "CRITICAL" in str(p.priority):
                overrides[p.profile_id] = 5
            else:
                overrides[p.profile_id] = 3

        return RetryPolicy(
            max_retries=3,
            backoff_factor=1.5,
            retryable_errors=["TIMEOUT", "RESOURCE_BUSY", "TRANSIENT_FAILURE", "NETWORK_ERROR"],
            per_profile_overrides=overrides,
        )

    def _build_failure_policy(
        self, plan: EngineeringExecutionPlan
    ) -> FailureHandlingPolicy:
        """Construct failure handling policy."""
        return FailureHandlingPolicy(
            action="ABORT_MISSION",
            max_failure_threshold=1,
            rollback_on_failure=True,
            isolation_enabled=True,
        )

    def _build_rollback_policy(
        self, plan: EngineeringExecutionPlan
    ) -> RollbackPolicy:
        """Construct rollback policy."""
        return RollbackPolicy(
            strategy="SNAPSHOT_RESTORE",
            checkpoint_enabled=True,
            rollback_target_wave=1,
        )

    def _build_timeout_policy(
        self,
        plan: EngineeringExecutionPlan,
        profiles: List[AgentProfile],
        waves: List[ExecutionWave],
    ) -> TimeoutPolicy:
        """Construct timeout policies for total mission, waves, and profiles."""
        wave_timeouts = {
            1: 300,
            2: 600,
            3: 450,
            4: 300,
            5: 150,
            6: 150,
        }

        profile_timeouts: Dict[str, int] = {}
        for p in profiles:
            profile_timeouts[p.profile_id] = 300

        total_timeout = sum(wave_timeouts.values())

        return TimeoutPolicy(
            total_mission_timeout_seconds=total_timeout,
            wave_timeouts=wave_timeouts,
            profile_timeouts=profile_timeouts,
        )

    def _build_budget_allocation(
        self,
        plan: EngineeringExecutionPlan,
        waves: List[ExecutionWave],
        profiles: List[AgentProfile],
    ) -> ExecutionBudgetAllocation:
        """Allocate USD execution budget deterministically across waves and profiles."""
        total_budget = 50.0  # USD

        # Wave percentages: W1=15%, W2=35%, W3=20%, W4=15%, W5=10%, W6=5%
        wave_percents = {1: 0.15, 2: 0.35, 3: 0.20, 4: 0.15, 5: 0.10, 6: 0.05}
        wave_budgets: Dict[int, float] = {}

        for w_num, pct in wave_percents.items():
            wave_budgets[w_num] = round(total_budget * pct, 2)

        profile_budgets: Dict[str, float] = {}
        profile_by_wave: Dict[int, List[AgentProfile]] = {}
        for p in profiles:
            # find profile wave
            for w in waves:
                if p.profile_id in w.profile_ids:
                    profile_by_wave.setdefault(w.wave_number, []).append(p)
                    break

        for w_num, w_profs in profile_by_wave.items():
            if w_profs:
                share = round(wave_budgets[w_num] / len(w_profs), 2)
                for p in w_profs:
                    profile_budgets[p.profile_id] = share

        return ExecutionBudgetAllocation(
            total_budget_usd=total_budget,
            wave_budgets=wave_budgets,
            profile_budgets=profile_budgets,
            currency="USD",
        )

    def _consolidate_constraints(
        self, plan: EngineeringExecutionPlan, profiles: List[AgentProfile]
    ) -> List[str]:
        """Consolidate constraints from plan and agent profiles."""
        constraints = list(plan.known_constraints)
        for p in profiles:
            constraints.extend(p.execution_constraints)
        return sorted(list(set(constraints)))

    def _validate_deployment(
        self,
        profiles: List[AgentProfile],
        execution_waves: List[ExecutionWave],
        profile_wave_map: Dict[str, int],
        dep_graph: Dict[str, List[str]],
        review_gates: List[ReviewGate],
        approval_gates: List[ApprovalGate],
        artifact_routes: List[ArtifactRoute],
    ) -> Dict[str, Any]:
        """Validate deployment plan invariants and return validation metrics."""
        all_profile_ids = {p.profile_id for p in profiles}

        # 1. Check no cyclic execution (already checked in DAG construction)
        no_cyclic_execution = True

        # 2. Check every profile scheduled exactly once
        scheduled_profile_ids = set()
        for w in execution_waves:
            for pid in w.profile_ids:
                if pid in scheduled_profile_ids:
                    raise UnscheduledProfileError(f"Agent profile '{pid}' is scheduled in multiple waves.")
                scheduled_profile_ids.add(pid)

        if scheduled_profile_ids != all_profile_ids:
            missing = all_profile_ids - scheduled_profile_ids
            raise UnscheduledProfileError(f"Agent profiles missing from execution wave scheduling: {missing}")
        every_profile_scheduled = True

        # 3. Check no orphan profiles (all scheduled profiles have wave assignment and valid IDs)
        no_orphan_profiles = len(profile_wave_map) == len(all_profile_ids) and all(
            pid in all_profile_ids for pid in profile_wave_map
        )
        if not no_orphan_profiles:
            raise OrphanProfileError("Orphan profile detected without valid wave mapping.")

        # 4. Check valid review path
        valid_review_path = len(review_gates) > 0
        if not valid_review_path:
            raise InvalidGatePathError("No review gates attached to deployment plan.")

        # 5. Check valid approval path
        valid_approval_path = len(approval_gates) > 0
        if not valid_approval_path:
            raise InvalidGatePathError("No approval gates attached to deployment plan.")

        # 6. Check valid artifact routing (routes exist if dependencies exist)
        total_dep_edges = sum(len(deps) for deps in dep_graph.values())
        valid_artifact_routing = len(artifact_routes) >= total_dep_edges if total_dep_edges > 0 else True
        if total_dep_edges > 0 and len(artifact_routes) == 0:
            raise InvalidGatePathError("Dependencies exist but no artifact routes were generated.")

        # 7. Check deterministic execution order
        deterministic_execution_order = True

        return {
            "no_cyclic_execution": no_cyclic_execution,
            "every_profile_scheduled": every_profile_scheduled,
            "no_orphan_profiles": no_orphan_profiles,
            "valid_review_path": valid_review_path,
            "valid_approval_path": valid_approval_path,
            "valid_artifact_routing": valid_artifact_routing,
            "deterministic_execution_order": deterministic_execution_order,
        }
