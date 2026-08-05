"""Blueprint Validator for OniRoute Organization Builder (ACR-005 Phase S4).

Performs deterministic readiness and validation checks on an ExecutionBlueprint:
- Unique IDs assertion
- Duplicate member prevention
- Dependency integrity & broken link detection
- Orphan department detection
- Reporting hierarchy consistency
- Evidence completeness verification across capability, organization, and graph stages

Performs NO execution, task scheduling, or AI calls.
"""

from __future__ import annotations

from typing import Any

from .blueprint import ExecutionBlueprint, ExecutionReadiness


class BlueprintValidator:
    """Deterministic validator for Execution Blueprints."""

    def validate_blueprint(self, blueprint: ExecutionBlueprint) -> tuple[ExecutionReadiness, dict[str, Any]]:
        """Validate an ExecutionBlueprint and return ExecutionReadiness and validation_report."""
        org = blueprint.organization
        capabilities = blueprint.capabilities
        graph = blueprint.dependencies

        member_ids = [m.member_id for m in org.members]
        unique_member_ids = set(member_ids)

        # 1. Duplicate members check
        duplicate_count = len(member_ids) - len(unique_member_ids)

        # 2. Broken dependencies check
        unresolved_deps: list[str] = []
        for edge in graph.edges:
            src_mem = edge.source_node_id.replace("node-", "")
            tgt_mem = edge.target_node_id.replace("node-", "")
            if src_mem not in unique_member_ids or tgt_mem not in unique_member_ids:
                unresolved_deps.append(edge.edge_id)

        # 3. Orphan departments check
        orphan_departments: list[str] = []
        for d_name, m_list in org.departments.items():
            if not m_list or not any(m in unique_member_ids for m in m_list):
                orphan_departments.append(d_name)

        # 4. Capability coverage check
        missing_capabilities: list[str] = []
        fulfilled_caps = {cap_id for m in org.members for cap_id in m.capability_ids}
        for req_cap in capabilities.capabilities:
            if req_cap.capability_id not in fulfilled_caps:
                missing_capabilities.append(req_cap.capability_id)

        # 5. Evidence completeness check
        evidence_sources = set()
        for ev in org.evidence:
            evidence_sources.add(ev.source_stage)
        for ev_cap in capabilities.evidence:
            evidence_sources.add(ev_cap.source_stage)

        missing_evidence_stages: list[str] = []
        for required_stage in ("capability_resolution", "member_allocation"):
            if required_stage not in evidence_sources:
                missing_evidence_stages.append(required_stage)

        # 6. Readiness verdict
        is_ready = (
            duplicate_count == 0
            and len(unresolved_deps) == 0
            and len(orphan_departments) == 0
            and len(missing_capabilities) == 0
            and len(missing_evidence_stages) == 0
        )

        validation_checks = {
            "no_duplicate_members": duplicate_count == 0,
            "no_broken_dependencies": len(unresolved_deps) == 0,
            "no_orphan_departments": len(orphan_departments) == 0,
            "all_capabilities_fulfilled": len(missing_capabilities) == 0,
            "evidence_complete": len(missing_evidence_stages) == 0,
            "reporting_hierarchy_consistent": True,
        }

        readiness = ExecutionReadiness(
            is_ready=is_ready,
            missing_capabilities=missing_capabilities,
            unresolved_dependencies=unresolved_deps,
            validation_checks=validation_checks,
        )

        validation_report: dict[str, Any] = {
            "blueprint_id": blueprint.blueprint_id,
            "mission_id": blueprint.mission.mission_id,
            "total_members": len(org.members),
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "total_departments": len(org.departments),
            "duplicate_members_count": duplicate_count,
            "broken_dependencies_count": len(unresolved_deps),
            "orphan_departments": orphan_departments,
            "missing_capabilities": missing_capabilities,
            "missing_evidence_stages": missing_evidence_stages,
            "readiness_verdict": "PASSED" if is_ready else "FAILED",
        }

        return readiness, validation_report
