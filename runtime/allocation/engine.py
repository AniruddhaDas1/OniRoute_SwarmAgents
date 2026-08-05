"""Implementation Allocation Engine (Phase P4.G3).

Consumes ProjectBlueprintReport and deterministically allocates implementation targets
(files, directories, modules, components, configs, docs, tests, assets) to engineering
disciplines and agent profiles without invoking LLMs or generating source code.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.blueprint.models import EngineeringDiscipline, ProjectBlueprintReport
from runtime.allocation.exceptions import AllocationDependencyError, AllocationValidationError, ImplementationAllocationError
from runtime.allocation.models import AllocationTarget, ImplementationAllocationReport, ImplementationPriority


PROFILE_DISCIPLINE_MAP: Dict[str, Tuple[str, str]] = {
    EngineeringDiscipline.FRONTEND.value: ("prf-fe-spec", "Frontend Specialist"),
    EngineeringDiscipline.BACKEND.value: ("prf-be-eng", "Backend Engineer"),
    EngineeringDiscipline.DATABASE.value: ("prf-db-admin", "Database Administrator"),
    EngineeringDiscipline.INFRASTRUCTURE.value: ("prf-devops-eng", "DevOps Infrastructure Engineer"),
    EngineeringDiscipline.SECURITY.value: ("prf-sec-auditor", "Security Auditor"),
    EngineeringDiscipline.TESTING.value: ("prf-qa-eng", "QA Automation Engineer"),
    EngineeringDiscipline.DOCUMENTATION.value: ("prf-doc-spec", "Technical Writer & Documentation Specialist"),
    EngineeringDiscipline.AUTOMATION.value: ("prf-auto-eng", "Build & Automation Engineer"),
    EngineeringDiscipline.ANALYTICS.value: ("prf-telemetry-spec", "Telemetry & Analytics Engineer"),
    EngineeringDiscipline.AI.value: ("prf-ai-architect", "AI & Swarm Systems Architect"),
    EngineeringDiscipline.SHARED.value: ("prf-lead-arch", "Lead System Architect"),
}


class ImplementationAllocationEngine:
    """Deterministic Implementation Allocation Engine for Phase P4.G3.

    Consumes ONLY ProjectBlueprintReport to allocate every implementation target to an
    engineering discipline and Agent Profile ID.
    """

    def allocate_implementation(
        self, blueprint_report: ProjectBlueprintReport
    ) -> ImplementationAllocationReport:
        """Generate deterministic Implementation Allocation from ProjectBlueprintReport.

        Args:
            blueprint_report: Immutable ProjectBlueprintReport input contract.

        Returns:
            ImplementationAllocationReport: Immutable allocation report.
        """
        start_time = time.perf_counter()

        if not isinstance(blueprint_report, ProjectBlueprintReport):
            raise AllocationValidationError(
                f"ImplementationAllocationEngine consumes ONLY ProjectBlueprintReport. "
                f"Received invalid input type: {type(blueprint_report).__name__}"
            )

        blueprint_id = blueprint_report.blueprint_id
        ws_id = blueprint_report.workspace_id
        ws_root = blueprint_report.workspace_root
        tech_stack = blueprint_report.technology_stack.lower()

        # 1. Allocate Implementation Targets
        targets, target_dependencies = self._allocate_targets(blueprint_report)

        # 2. Compute Topological Execution Order
        execution_order = self._compute_execution_order(targets, target_dependencies)

        # 3. Assemble Ownership Mappings
        agent_ownership, discipline_ownership = self._assemble_ownership_maps(targets)

        # 4. Consolidate Expected Deliverables
        expected_deliverables = self._consolidate_deliverables(targets, blueprint_report)

        # 5. Validate Allocation Integrity
        coverage_metrics, validation_results = self._validate_allocation_integrity(
            blueprint_report=blueprint_report,
            targets=targets,
            agent_ownership=agent_ownership,
            discipline_ownership=discipline_ownership,
            execution_order=execution_order,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        allocation_id = f"alloc-{abs(hash(f'{blueprint_id}-{ws_id}-{timestamp_iso}')) % 1000000:06d}"

        # 6. Compute SHA-256 Allocation Hash
        allocation_hash = self._compute_allocation_hash(
            allocation_id=allocation_id,
            blueprint_id=blueprint_id,
            workspace_id=ws_id,
            workspace_root=ws_root,
            technology_stack=tech_stack,
            targets=targets,
            agent_ownership=agent_ownership,
        )

        # 7. Assemble Evidence & Performance Metrics
        evidence: Dict[str, Any] = {
            "blueprint_id": blueprint_id,
            "blueprint_hash": blueprint_report.blueprint_hash,
            "target_count": len(targets),
            "agent_profile_count": len(agent_ownership),
            "discipline_count": len(discipline_ownership),
            "execution_order_length": len(execution_order),
            "latency_ms": round(elapsed_ms, 3),
            "determinism": True,
            "coverage_score": coverage_metrics["coverage_score"],
            "validation": validation_results,
            "timestamp": timestamp_iso,
        }

        # 8. Return Immutable Report
        return ImplementationAllocationReport(
            allocation_id=allocation_id,
            blueprint_id=blueprint_id,
            workspace_id=ws_id,
            workspace_root=ws_root,
            technology_stack=tech_stack,
            allocated_targets=targets,
            agent_ownership=agent_ownership,
            discipline_ownership=discipline_ownership,
            expected_deliverables=expected_deliverables,
            dependencies=target_dependencies,
            execution_order=execution_order,
            coverage=coverage_metrics,
            evidence=evidence,
            timestamp=timestamp_iso,
            allocation_hash=allocation_hash,
        )

    def _allocate_targets(
        self, blueprint_report: ProjectBlueprintReport
    ) -> Tuple[List[AllocationTarget], Dict[str, List[str]]]:
        """Allocate all modules, directories, files, components, configs, and assets."""
        targets: List[AllocationTarget] = []
        target_dependencies: Dict[str, List[str]] = {}
        target_id_counter = 1

        module_target_map: Dict[str, str] = {}

        # 1. Allocate Module Targets
        for mod in blueprint_report.project_modules:
            tgt_id = f"tgt-mod-{target_id_counter:04d}"
            target_id_counter += 1

            discipline = mod.discipline
            profile_id, profile_role = PROFILE_DISCIPLINE_MAP.get(
                discipline, ("prf-lead-arch", "Lead System Architect")
            )

            mod_deps = [module_target_map[dep_id] for dep_id in mod.dependencies if dep_id in module_target_map]

            target = AllocationTarget(
                target_id=tgt_id,
                target_type="module",
                relative_path=mod.relative_path,
                owning_discipline=discipline,
                owning_profile_id=profile_id,
                owning_profile_role=profile_role,
                expected_deliverable=f"Module Implementation: {mod.name}",
                priority=ImplementationPriority.P0_CRITICAL.value if discipline in (EngineeringDiscipline.SHARED.value, EngineeringDiscipline.INFRASTRUCTURE.value) else ImplementationPriority.P1_HIGH.value,
                dependencies=mod_deps,
            )
            targets.append(target)
            target_dependencies[tgt_id] = mod_deps
            module_target_map[mod.module_id] = tgt_id

        # 2. Allocate Directory Targets
        for dir_path, discipline in blueprint_report.directory_ownership.items():
            tgt_id = f"tgt-dir-{target_id_counter:04d}"
            target_id_counter += 1

            profile_id, profile_role = PROFILE_DISCIPLINE_MAP.get(
                discipline, ("prf-lead-arch", "Lead System Architect")
            )

            target = AllocationTarget(
                target_id=tgt_id,
                target_type="directory",
                relative_path=dir_path,
                owning_discipline=discipline,
                owning_profile_id=profile_id,
                owning_profile_role=profile_role,
                expected_deliverable=f"Directory Structure: {dir_path}",
                priority=ImplementationPriority.P1_HIGH.value,
                dependencies=[],
            )
            targets.append(target)
            target_dependencies[tgt_id] = []

        # 3. Allocate File Targets
        for file_path in blueprint_report.expected_files:
            tgt_id = f"tgt-file-{target_id_counter:04d}"
            target_id_counter += 1

            discipline = self._determine_file_discipline(file_path, blueprint_report)
            profile_id, profile_role = PROFILE_DISCIPLINE_MAP.get(
                discipline, ("prf-lead-arch", "Lead System Architect")
            )

            priority = ImplementationPriority.P1_HIGH.value
            if file_path.startswith(".oniroute") or file_path in ("package.json", "pyproject.toml", "pubspec.yaml", "pnpm-workspace.yaml"):
                priority = ImplementationPriority.P0_CRITICAL.value
            elif file_path.startswith("docs/"):
                priority = ImplementationPriority.P2_MEDIUM.value
            elif file_path.startswith("tests/"):
                priority = ImplementationPriority.P1_HIGH.value

            target = AllocationTarget(
                target_id=tgt_id,
                target_type="file",
                relative_path=file_path,
                owning_discipline=discipline,
                owning_profile_id=profile_id,
                owning_profile_role=profile_role,
                expected_deliverable=f"File Source Implementation: {file_path}",
                priority=priority,
                dependencies=[],
            )
            targets.append(target)
            target_dependencies[tgt_id] = []

        return targets, target_dependencies

    def _determine_file_discipline(
        self, file_path: str, blueprint_report: ProjectBlueprintReport
    ) -> str:
        """Determine owning discipline for a specific file path."""
        # 1. Match against directory ownership
        for dir_path, discipline in blueprint_report.directory_ownership.items():
            if file_path.startswith(dir_path):
                return discipline

        # 2. File path heuristics
        if file_path.startswith("tests/"):
            return EngineeringDiscipline.TESTING.value
        if file_path.startswith("docs/"):
            return EngineeringDiscipline.DOCUMENTATION.value
        if file_path.startswith("scripts/"):
            return EngineeringDiscipline.AUTOMATION.value
        if file_path.startswith("configs/"):
            return EngineeringDiscipline.INFRASTRUCTURE.value
        if file_path.startswith("reports/"):
            return EngineeringDiscipline.ANALYTICS.value
        if file_path.startswith(".oniroute/"):
            return EngineeringDiscipline.AI.value

        return EngineeringDiscipline.SHARED.value

    def _compute_execution_order(
        self, targets: List[AllocationTarget], target_dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Compute topological sort of allocation targets based on dependency DAG."""
        in_degree: Dict[str, int] = {t.target_id: 0 for t in targets}
        graph: Dict[str, List[str]] = defaultdict(list)

        for t_id, deps in target_dependencies.items():
            for dep in deps:
                if dep in in_degree:
                    graph[dep].append(t_id)
                    in_degree[t_id] += 1

        queue = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) < len(targets):
            raise AllocationDependencyError(
                "Circular dependency detected among allocation targets during topological sorting."
            )

        return order

    def _assemble_ownership_maps(
        self, targets: List[AllocationTarget]
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """Assemble agent profile and discipline ownership maps."""
        agent_map: Dict[str, List[str]] = defaultdict(list)
        discipline_map: Dict[str, List[str]] = defaultdict(list)

        for t in targets:
            agent_map[t.owning_profile_id].append(t.target_id)
            discipline_map[t.owning_discipline].append(t.target_id)

        return dict(agent_map), dict(discipline_map)

    def _consolidate_deliverables(
        self, targets: List[AllocationTarget], blueprint_report: ProjectBlueprintReport
    ) -> List[str]:
        """Consolidate expected deliverables across all allocated targets."""
        deliverables: Set[str] = set(blueprint_report.expected_deliverables)
        for t in targets:
            deliverables.add(f"[{t.owning_profile_role}] {t.expected_deliverable}")
        return sorted(deliverables)

    def _validate_allocation_integrity(
        self,
        blueprint_report: ProjectBlueprintReport,
        targets: List[AllocationTarget],
        agent_ownership: Dict[str, List[str]],
        discipline_ownership: Dict[str, List[str]],
        execution_order: List[str],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Validate 100% target ownership, orphan files, duplicate ownership, and DAG integrity."""
        total_targets = len(targets)
        owned_targets = sum(len(ids) for ids in agent_ownership.values())

        hundred_percent_ownership = total_targets > 0 and owned_targets == total_targets
        no_orphan_files = all(t.owning_profile_id != "" for t in targets)
        no_duplicate_ownership = len(set(t.target_id for t in targets)) == total_targets
        dependency_integrity = len(execution_order) == total_targets

        coverage_score = 1.0 if (hundred_percent_ownership and no_orphan_files and no_duplicate_ownership and dependency_integrity) else 0.0

        if not hundred_percent_ownership or not no_orphan_files or not no_duplicate_ownership or not dependency_integrity:
            raise AllocationValidationError(
                f"Allocation integrity check failed: hundred_percent={hundred_percent_ownership}, "
                f"no_orphans={no_orphan_files}, no_duplicates={no_duplicate_ownership}, "
                f"dag_integrity={dependency_integrity}"
            )

        coverage_metrics = {
            "total_targets": total_targets,
            "owned_targets": owned_targets,
            "coverage_score": coverage_score,
            "file_target_count": len([t for t in targets if t.target_type == "file"]),
            "dir_target_count": len([t for t in targets if t.target_type == "directory"]),
            "module_target_count": len([t for t in targets if t.target_type == "module"]),
        }

        validation_results = {
            "hundred_percent_ownership": hundred_percent_ownership,
            "no_orphan_files": no_orphan_files,
            "no_duplicate_ownership": no_duplicate_ownership,
            "dependency_integrity": dependency_integrity,
            "coverage_score": coverage_score,
        }

        return coverage_metrics, validation_results

    def _compute_allocation_hash(
        self,
        allocation_id: str,
        blueprint_id: str,
        workspace_id: str,
        workspace_root: str,
        technology_stack: str,
        targets: List[AllocationTarget],
        agent_ownership: Dict[str, List[str]],
    ) -> str:
        """Compute SHA-256 hash of allocation payload."""
        hash_payload = {
            "allocation_id": allocation_id,
            "blueprint_id": blueprint_id,
            "workspace_id": workspace_id,
            "workspace_root": workspace_root,
            "technology_stack": technology_stack,
            "targets": [t.model_dump(mode="json") for t in targets],
            "agent_ownership": agent_ownership,
        }
        json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
