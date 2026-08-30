"""E2.2 Contract Decomposition Engine (Phase E2.2).

Deterministic engine that decomposes EngineeringContractReport into
sub-contracts, dependency graphs, artifact routes, and execution waves.

No LLM calls, no agent execution, no code generation.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.contracts.decomposition import (
    ArtifactRoute,
    ContractDecompositionReport,
    ContractDecompositionValidator,
    DependencyEdge,
    DependencyGraph,
    DependencyType,
    DecompositionCoverageMetrics,
    ExecutionWave,
    ParallelExecutionGroup,
    SubContract,
)
from runtime.contracts.models import EngineeringContract, EngineeringContractReport


class ContractDecompositionEngine:
    """Deterministic engine that decomposes EngineeringContractReport into
    ContractDecompositionReport.

    Consumes: EngineeringContractReport
    Produces: ContractDecompositionReport with sub-contracts, dependency graph,
              artifact routes, execution waves, and parallel execution groups.

    No LLM calls, no agent execution, no code generation.
    """

    def decompose(
        self,
        contract_report: EngineeringContractReport,
    ) -> ContractDecompositionReport:
        """Decompose an EngineeringContractReport into sub-contracts and execution structure.

        Args:
            contract_report: Immutable EngineeringContractReport from E2.1.

        Returns:
            ContractDecompositionReport: Immutable decomposition output.

        Raises:
            ContractDecompositionError: If decomposition or validation fails.
        """
        if not isinstance(contract_report, EngineeringContractReport):
            raise ContractDecompositionError(
                f"Expected EngineeringContractReport, got {type(contract_report).__name__}"
            )

        mission_id = contract_report.mission_id
        plan_id = contract_report.execution_plan_id
        report_id = contract_report.report_id

        # 1. Decompose contracts into sub-contracts
        (
            sub_contracts,
            deliverable_to_sub_contract,
            artifact_routes,
            contract_index,
        ) = self._decompose_contracts(contract_report)

        # 2. Build dependency graph
        dependency_graph = self._build_dependency_graph(
            sub_contracts, deliverable_to_sub_contract, contract_index
        )

        # 3. Compute execution waves
        execution_waves = self._compute_execution_waves(sub_contracts, dependency_graph)

        # 4. Identify parallel execution groups
        parallel_groups = self._compute_parallel_groups(
            sub_contracts, execution_waves, dependency_graph
        )

        # 5. Compute coverage metrics
        coverage = self._compute_coverage(
            contract_report, sub_contracts, artifact_routes
        )

        # 6. Validate decomposition
        validator = ContractDecompositionValidator()
        validation_results = validator.validate(
            contract_report=contract_report,
            sub_contracts=sub_contracts,
            dependency_graph=dependency_graph,
            execution_waves=execution_waves,
        )

        # 7. Build traceability
        traceability = {
            "mission_id": mission_id,
            "execution_plan_id": plan_id,
            "contract_report_id": report_id,
            "parent_contract_count": str(len(contract_report.contracts)),
            "sub_contract_count": str(len(sub_contracts)),
        }

        # 8. Compute deterministic hashes
        decomposition_report_id = self._compute_report_id(report_id)
        report_hash = self._compute_report_hash(
            decomposition_report_id, report_id, sub_contracts, dependency_graph, execution_waves
        )

        # 9. Assemble report
        total_waves = len(execution_waves)
        timestamp = datetime.now(timezone.utc).isoformat()

        decomposition_report = ContractDecompositionReport(
            report_id=decomposition_report_id,
            mission_id=mission_id,
            parent_contract_report_id=report_id,
            sub_contracts=sub_contracts,
            dependency_graph=dependency_graph,
            artifact_routes=artifact_routes,
            execution_waves=execution_waves,
            parallel_execution_groups=parallel_groups,
            coverage=coverage.model_dump(mode="json"),
            validation_results=validation_results,
            traceability=traceability,
            deterministic=True,
            report_hash=report_hash,
            total_sub_contracts=len(sub_contracts),
            total_waves=total_waves,
            total_artifact_routes=len(artifact_routes),
            parallelizable_groups=len(parallel_groups),
            timestamp=timestamp,
        )

        return decomposition_report

    # -------------------------------------------------------------------------
    # E2.2.4 - Deliverable-level decomposition
    # -------------------------------------------------------------------------

    def _decompose_contracts(
        self,
        contract_report: EngineeringContractReport,
    ) -> Tuple[List[SubContract], Dict[str, str], List[ArtifactRoute], Dict[str, Any]]:
        """Decompose each contract into sub-contracts based on deliverables.

        Each contract with N deliverables produces up to N sub-contracts.
        Atomic contracts (no decomposition needed) produce 1 sub-contract.
        """
        sub_contracts: List[SubContract] = []
        deliverable_to_sub_contract: Dict[str, str] = {}
        artifact_routes: List[ArtifactRoute] = []
        contract_index: Dict[str, EngineeringContract] = {}

        for contract in contract_report.contracts:
            contract_index[contract.contract_id] = contract
            deliverables = [
                d for d in contract_report.deliverables
                if d.contract_id == contract.contract_id
            ]
            acceptance_criteria = [
                a for a in contract_report.acceptance_criteria_models
                if a.contract_id == contract.contract_id
            ]

            # E2.2.4: Use DeliverableContract as decomposition boundary
            if len(deliverables) <= 1:
                # Atomic contract: single sub-contract
                sub_ctr = self._make_atomic_sub_contract(
                    contract, deliverables, acceptance_criteria,
                    contract_report.mission_id, contract_report.execution_plan_id,
                    contract_report.bundle_report_id, contract_report.agent_profile_report_id,
                )
                sub_contracts.append(sub_ctr)
            else:
                # Multi-deliverable: one sub-contract per deliverable
                for idx, deliverable in enumerate(deliverables, start=1):
                    sub_ctr = self._make_sub_contract(
                        contract=contract,
                        deliverable=deliverable,
                        all_deliverables=deliverables,
                        acceptance_criteria=acceptance_criteria,
                        index=idx,
                        mission_id=contract_report.mission_id,
                        plan_id=contract_report.execution_plan_id,
                        bundle_report_id=contract_report.bundle_report_id,
                        profile_report_id=contract_report.agent_profile_report_id,
                    )
                    sub_contracts.append(sub_ctr)
                    deliverable_to_sub_contract[deliverable.deliverable_id] = sub_ctr.sub_contract_id

                    # E2.2.6: Build artifact route for each deliverable
                    route = self._make_artifact_route(
                        deliverable, sub_ctr, contract, idx
                    )
                    artifact_routes.append(route)

        return sub_contracts, deliverable_to_sub_contract, artifact_routes, contract_index

    def _make_atomic_sub_contract(
        self,
        contract: EngineeringContract,
        deliverables: List[Any],
        acceptance_criteria: List[Any],
        mission_id: str,
        plan_id: str,
        bundle_report_id: str,
        profile_report_id: str,
    ) -> SubContract:
        """Create a single sub-contract for an atomic (non-decomposed) contract."""
        contract_idx = int(contract.contract_id.split("-")[1])
        sctr_id = f"sctr-{contract.contract_id}-01"

        acceptance_criteria_text = [
            ac.description for ac in acceptance_criteria
        ] if acceptance_criteria else contract.acceptance_criteria

        deliverable_ids = [d.deliverable_id for d in deliverables]
        deliverable_descs = [d.description for d in deliverables] if deliverables else contract.expected_deliverables

        traceability = {
            "mission_id": mission_id,
            "execution_plan_id": plan_id,
            "bundle_report_id": bundle_report_id,
            "profile_report_id": profile_report_id,
            "contract_id": contract.contract_id,
            "deliverable_ids": ",".join(deliverable_ids) if deliverable_ids else "",
        }

        deterministic_hash = self._compute_sub_contract_hash(
            sctr_id, contract.contract_id, contract.skill_bundle_id, plan_id, mission_id
        )

        # Strip non-sub-contract dependencies (bundle IDs are not valid at sub-contract level)
        atomic_dependencies = [d for d in contract.dependencies if d.startswith("sctr-")]

        return SubContract(
            sub_contract_id=sctr_id,
            parent_contract_id=contract.contract_id,
            mission_id=mission_id,
            agent_profile_id=contract.agent_profile_id,
            skill_bundle_id=contract.skill_bundle_id,
            objective=contract.objective,
            required_capabilities=contract.required_capabilities,
            required_skills=contract.required_skills,
            inputs=contract.inputs,
            expected_deliverables=deliverable_descs,
            acceptance_criteria=acceptance_criteria_text,
            dependencies=atomic_dependencies,
            constraints=contract.constraints,
            repository_scope=contract.repository_scope,
            technology_context=contract.technology_context,
            priority=contract.generation_priority,
            execution_order=contract.execution_order,
            execution_wave=contract.execution_wave,
            risk_level=contract.risk_level,
            is_atomic=True,
            decomposition_reason="Atomic contract: no decomposition needed",
            owned_deliverables=deliverable_ids,
            traceability=traceability,
            deterministic_hash=deterministic_hash,
        )

    def _make_sub_contract(
        self,
        contract: EngineeringContract,
        deliverable: Any,
        all_deliverables: List[Any],
        acceptance_criteria: List[Any],
        index: int,
        mission_id: str,
        plan_id: str,
        bundle_report_id: str,
        profile_report_id: str,
    ) -> SubContract:
        """Create a sub-contract for a specific deliverable within a contract."""
        sctr_id = f"sctr-{contract.contract_id}-{index:02d}"

        # Inherit dependencies from parent, and add cross-deliverable dependencies
        dependencies = self._resolve_deliverable_dependencies(
            deliverable, all_deliverables, contract
        )

        # Acceptance criteria: filter to relevant ones or inherit all
        criteria_text = [
            ac.description for ac in acceptance_criteria
        ] if acceptance_criteria else contract.acceptance_criteria

        traceability = {
            "mission_id": mission_id,
            "execution_plan_id": plan_id,
            "bundle_report_id": bundle_report_id,
            "profile_report_id": profile_report_id,
            "contract_id": contract.contract_id,
            "deliverable_id": deliverable.deliverable_id,
        }

        deterministic_hash = self._compute_sub_contract_hash(
            sctr_id, contract.contract_id, deliverable.deliverable_id, plan_id, mission_id
        )

        return SubContract(
            sub_contract_id=sctr_id,
            parent_contract_id=contract.contract_id,
            mission_id=mission_id,
            agent_profile_id=contract.agent_profile_id,
            skill_bundle_id=contract.skill_bundle_id,
            objective=f"{contract.objective}: {deliverable.description}",
            required_capabilities=contract.required_capabilities,
            required_skills=contract.required_skills,
            inputs=contract.inputs,
            expected_deliverables=[deliverable.description],
            acceptance_criteria=criteria_text,
            dependencies=dependencies,
            constraints=contract.constraints,
            repository_scope=contract.repository_scope,
            technology_context=contract.technology_context,
            priority=contract.generation_priority,
            execution_order=contract.execution_order * 100 + index,
            execution_wave=contract.execution_wave,
            risk_level=contract.risk_level,
            is_atomic=False,
            decomposition_reason=f"Multi-deliverable contract: decomposed at deliverable '{deliverable.description}'",
            owned_deliverables=[deliverable.deliverable_id],
            traceability=traceability,
            deterministic_hash=deterministic_hash,
        )

    def _resolve_deliverable_dependencies(
        self,
        deliverable: Any,
        all_deliverables: List[Any],
        contract: EngineeringContract,
    ) -> List[str]:
        """Resolve dependencies for a deliverable.

        If parent contract has REQUIRES-style dependencies on other contracts,
        resolve them to sub-contract IDs.
        """
        # Strip parent contract IDs and bundle IDs - sub-contract dependencies
        # must only contain valid sub-contract IDs
        dependencies: List[str] = [
            d for d in contract.dependencies
            if d.startswith("sctr-")
        ]

        # For cross-deliverable dependencies within the same contract,
        # we track ordering by deliverable index
        deliverable_idx_map = {
            d.deliverable_id: idx
            for idx, d in enumerate(all_deliverables)
        }

        # Add implicit ordering dependencies for deliverables within same contract
        current_idx = deliverable_idx_map.get(deliverable.deliverable_id, 0)

        # If this is not the first deliverable, add dependencies on earlier ones
        for other_deliverable in all_deliverables:
            other_idx = deliverable_idx_map.get(other_deliverable.deliverable_id, 0)
            if other_idx < current_idx:
                # Earlier deliverable must complete first
                other_sctr_id = f"sctr-{contract.contract_id}-{other_idx + 1:02d}"
                if other_sctr_id not in dependencies:
                    dependencies.append(other_sctr_id)

        return sorted(set(dependencies))

    def _make_artifact_route(
        self,
        deliverable: Any,
        sub_contract: SubContract,
        contract: EngineeringContract,
        index: int,
    ) -> ArtifactRoute:
        """Build an ArtifactRoute for a deliverable."""
        route_id = f"artr-{sub_contract.sub_contract_id}"

        # Determine artifact type from deliverable type
        artifact_type = deliverable.deliverable_type.replace("_", " ")

        # Repository path from deliverable type and discipline
        deliverable_type = deliverable.deliverable_type
        repo_path = self._resolve_artifact_path(deliverable_type, contract)

        return ArtifactRoute(
            route_id=route_id,
            artifact_id=deliverable.deliverable_id,
            producing_sub_contract_id=sub_contract.sub_contract_id,
            consuming_sub_contract_ids=[],
            artifact_type=artifact_type,
            repository_path=repo_path,
            technology_context=contract.technology_context,
            is_optional=False,
        )

    def _resolve_artifact_path(
        self,
        deliverable_type: str,
        contract: EngineeringContract,
    ) -> str:
        """Resolve the repository path for a deliverable artifact."""
        base_scope = contract.repository_scope

        type_to_subpath = {
            "frontend_application": "components/",
            "api_endpoint": "handlers/",
            "database_schema": "schemas/",
            "migration": "migrations/",
            "auth_flow": "auth/",
            "tests": "test_",
            "documentation": "docs/",
            "component": "components/",
            "config": "config/",
            "shared": "shared/",
        }

        subpath = type_to_subpath.get(deliverable_type, "")
        return f"{base_scope}{subpath}"

    # -------------------------------------------------------------------------
    # E2.2.5 - Dependency graph construction
    # -------------------------------------------------------------------------

    def _build_dependency_graph(
        self,
        sub_contracts: List[SubContract],
        deliverable_map: Dict[str, str],
        contract_index: Dict[str, EngineeringContract],
    ) -> DependencyGraph:
        """Build the dependency graph for all sub-contracts using Kahn's algorithm."""
        graph_id = f"depgraph-{len(sub_contracts)}"

        nodes = [s.sub_contract_id for s in sub_contracts]
        edges: List[DependencyEdge] = []
        adjacency: Dict[str, List[str]] = defaultdict(list)
        reverse_adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {n: 0 for n in nodes}

        # Build sub-contract index
        sctr_index: Dict[str, SubContract] = {s.sub_contract_id: s for s in sub_contracts}

        for sub_ctr in sub_contracts:
            for dep_id in sub_ctr.dependencies:
                if dep_id in nodes:
                    edge = DependencyEdge(
                        from_id=dep_id,
                        to_id=sub_ctr.sub_contract_id,
                        dependency_type=DependencyType.REQUIRES,
                        artifact_id="",
                        is_blocking=True,
                    )
                    edges.append(edge)
                    adjacency[dep_id].append(sub_ctr.sub_contract_id)
                    reverse_adj[sub_ctr.sub_contract_id].append(dep_id)
                    in_degree[sub_ctr.sub_contract_id] += 1

        # Add cross-contract ordering dependencies from contract-level ordering
        # Contracts with higher execution_order depend on those with lower
        contract_ordering = [
            (c.execution_order, c.contract_id)
            for c in contract_index.values()
        ]
        contract_ordering.sort()

        for i, (order_i, ctr_id_i) in enumerate(contract_ordering):
            for j in range(i):
                _, ctr_id_j = contract_ordering[j]
                # ctr_id_i comes after ctr_id_j
                # Find sub-contracts of ctr_id_i that don't already have this dep
                for sctr in sub_contracts:
                    if sctr.parent_contract_id == ctr_id_i:
                        # Find the first sub-contract of ctr_id_j
                        for other_sctr in sub_contracts:
                            if other_sctr.parent_contract_id == ctr_id_j:
                                if other_sctr.sub_contract_id not in sctr.dependencies:
                                    edge = DependencyEdge(
                                        from_id=other_sctr.sub_contract_id,
                                        to_id=sctr.sub_contract_id,
                                        dependency_type=DependencyType.REQUIRES,
                                        artifact_id="",
                                        is_blocking=True,
                                    )
                                    edges.append(edge)
                                    adjacency[other_sctr.sub_contract_id].append(sctr.sub_contract_id)
                                    reverse_adj[sctr.sub_contract_id].append(other_sctr.sub_contract_id)
                                    in_degree[sctr.sub_contract_id] += 1
                                break

        # Kahn's algorithm to detect cycles
        is_acyclic = self._check_acyclic(nodes, adjacency, in_degree)

        return DependencyGraph(
            graph_id=graph_id,
            nodes=sorted(nodes),
            edges=edges,
            adjacency=dict(adjacency),
            reverse_adjacency=dict(reverse_adj),
            in_degree=in_degree,
            is_acyclic=is_acyclic,
        )

    def _check_acyclic(
        self,
        nodes: List[str],
        adjacency: Dict[str, List[str]],
        in_degree: Dict[str, int],
    ) -> bool:
        """Check acyclicity using Kahn's topological sort."""
        queue = deque([n for n in nodes if in_degree.get(n, 0) == 0])
        visited = 0
        temp_in_degree = dict(in_degree)

        while queue:
            node = queue.popleft()
            visited += 1
            for neighbor in adjacency.get(node, []):
                temp_in_degree[neighbor] -= 1
                if temp_in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited == len(nodes)

    # -------------------------------------------------------------------------
    # E2.2.7 - Execution wave computation
    # -------------------------------------------------------------------------

    def _compute_execution_waves(
        self,
        sub_contracts: List[SubContract],
        dependency_graph: DependencyGraph,
    ) -> List[ExecutionWave]:
        """Compute deterministic execution waves using topological sort."""
        nodes = [s.sub_contract_id for s in sub_contracts]
        in_degree = dict(dependency_graph.in_degree)
        adj = dict(dependency_graph.adjacency)

        queue = deque([n for n in nodes if in_degree.get(n, 0) == 0])
        wave_map: Dict[str, int] = {}

        wave_num = 1
        while queue:
            current_wave = []
            next_queue = deque()

            while queue:
                node = queue.popleft()
                wave_map[node] = wave_num
                current_wave.append(node)

            for node in current_wave:
                for neighbor in adj.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0 and neighbor not in wave_map:
                        next_queue.append(neighbor)

            wave_num += 1
            queue = next_queue

        # Build ExecutionWave objects
        wave_sub_contracts: Dict[int, List[str]] = defaultdict(list)
        for sctr_id, wave in wave_map.items():
            wave_sub_contracts[wave].append(sctr_id)

        wave_names = self._assign_wave_names(wave_sub_contracts, sub_contracts)
        waves: List[ExecutionWave] = []
        for wave_num in sorted(wave_sub_contracts.keys()):
            sctr_ids = sorted(wave_sub_contracts[wave_num])
            blocking = [
                w
                for w in range(1, wave_num)
                if any(
                    wave_sub_contracts[w][i] in adj
                    for sctr_id in sctr_ids
                    for i in range(len(sctr_ids))
                )
            ]
            wave_artifacts = [
                d_id
                for sctr in sub_contracts
                if sctr.sub_contract_id in sctr_ids
                for d_id in sctr.owned_deliverables
            ]

            waves.append(
                ExecutionWave(
                    wave_number=wave_num,
                    wave_name=wave_names.get(wave_num, f"Wave {wave_num}"),
                    sub_contract_ids=sctr_ids,
                    parallelizable=True,
                    blocking_waves=blocking,
                    produced_artifacts=wave_artifacts,
                )
            )

        return waves

    def _assign_wave_names(
        self,
        wave_sub_contracts: Dict[int, List[str]],
        sub_contracts: List[SubContract],
    ) -> Dict[int, str]:
        """Assign human-readable names to execution waves based on contained disciplines."""
        sctr_map = {s.sub_contract_id: s for s in sub_contracts}
        names: Dict[int, str] = {}

        for wave_num, sctr_ids in sorted(wave_sub_contracts.items()):
            disciplines = set()
            for sctr_id in sctr_ids:
                sctr = sctr_map.get(sctr_id)
                if sctr:
                    disciplines.add(sctr.traceability.get("engineering_discipline", ""))

            if not disciplines:
                names[wave_num] = f"Wave {wave_num}"
            elif len(disciplines) == 1:
                names[wave_num] = f"{list(disciplines)[0]} Implementation"
            else:
                names[wave_num] = f"Multi-Discipline Wave {wave_num}"

        return names

    # -------------------------------------------------------------------------
    # E2.2.8 - Parallel execution groups
    # -------------------------------------------------------------------------

    def _compute_parallel_groups(
        self,
        sub_contracts: List[SubContract],
        execution_waves: List[ExecutionWave],
        dependency_graph: DependencyGraph,
    ) -> List[ParallelExecutionGroup]:
        """Identify sub-contracts that can safely execute in parallel."""
        groups: List[ParallelExecutionGroup] = []
        sctr_map = {s.sub_contract_id: s for s in sub_contracts}

        for wave in execution_waves:
            # All sub-contracts in a wave with no intra-wave dependencies are parallel
            wave_sctrs = wave.sub_contract_ids
            reverse_adj = dependency_graph.reverse_adjacency

            # Find blocking dependencies within the same wave
            blocking: Set[str] = set()
            required_inputs: Set[str] = set()
            produced_outputs: Set[str] = set()

            for sctr_id in wave_sctrs:
                sctr = sctr_map.get(sctr_id)
                if not sctr:
                    continue

                # Add owned deliverables as produced outputs
                produced_outputs.update(sctr.owned_deliverables)

                # Track dependencies that are within the same wave
                for dep_id in sctr.dependencies:
                    if dep_id in wave_sctrs:
                        blocking.add(dep_id)

                # Track inputs required
                required_inputs.update(sctr.inputs)

            # Only create a parallel group if not all are blocking each other
            if wave_sctrs:
                is_parallel = len(blocking) == 0

                groups.append(
                    ParallelExecutionGroup(
                        group_id=f"peg-wave{wave.wave_number}",
                        wave_number=wave.wave_number,
                        sub_contract_ids=sorted(wave_sctrs),
                        blocking_dependencies=sorted(blocking),
                        required_inputs=sorted(required_inputs),
                        produced_outputs=sorted(produced_outputs),
                    )
                )

        return groups

    # -------------------------------------------------------------------------
    # E2.2.11 - Coverage metrics
    # -------------------------------------------------------------------------

    def _compute_coverage(
        self,
        contract_report: EngineeringContractReport,
        sub_contracts: List[SubContract],
        artifact_routes: List[ArtifactRoute],
    ) -> DecompositionCoverageMetrics:
        """Compute decomposition coverage metrics."""
        total_contracts = len(contract_report.contracts)
        total_deliverables = len(contract_report.deliverables)
        total_acceptance = len(contract_report.acceptance_criteria_models)

        decomposed = sum(1 for s in sub_contracts if not s.is_atomic)
        atomic = sum(1 for s in sub_contracts if s.is_atomic)
        covered_deliverables = sum(len(s.owned_deliverables) for s in sub_contracts)
        covered_acceptance = sum(len(s.acceptance_criteria) for s in sub_contracts)
        routed_artifacts = len([r for r in artifact_routes if r.consuming_sub_contract_ids or r.repository_path])

        coverage_percent = 100.0
        if total_deliverables > 0:
            coverage_percent = min(100.0, (covered_deliverables / total_deliverables) * 100.0)

        return DecompositionCoverageMetrics(
            total_parent_contracts=total_contracts,
            decomposed_contracts=decomposed,
            atomic_contracts=atomic,
            total_sub_contracts=len(sub_contracts),
            total_deliverables=total_deliverables,
            covered_deliverables=covered_deliverables,
            total_acceptance_criteria=total_acceptance,
            covered_acceptance_criteria=covered_acceptance,
            total_artifacts=total_deliverables,
            routed_artifacts=routed_artifacts,
            coverage_percent=coverage_percent,
        )

    # -------------------------------------------------------------------------
    # Determinism helpers
    # -------------------------------------------------------------------------

    def _compute_report_id(self, contract_report_id: str) -> str:
        """Compute deterministic report ID."""
        payload = f"e22-{contract_report_id}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"cdcr-{digest}"

    def _compute_sub_contract_hash(
        self,
        sctr_id: str,
        contract_id: str,
        bundle_id: str,
        plan_id: str,
        mission_id: str,
    ) -> str:
        """Compute deterministic SHA-256 hash for a sub-contract."""
        payload = f"{sctr_id}:{contract_id}:{bundle_id}:{plan_id}:{mission_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _compute_report_hash(
        self,
        report_id: str,
        parent_report_id: str,
        sub_contracts: List[SubContract],
        dependency_graph: DependencyGraph,
        execution_waves: List[ExecutionWave],
    ) -> str:
        """Compute SHA-256 hash of entire decomposition report."""
        hash_payload = {
            "report_id": report_id,
            "parent_report_id": parent_report_id,
            "sub_contracts": [s.model_dump(mode="json") for s in sub_contracts],
            "graph_nodes": sorted(dependency_graph.nodes),
            "wave_numbers": [w.wave_number for w in execution_waves],
        }
        json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
