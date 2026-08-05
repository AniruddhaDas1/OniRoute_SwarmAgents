"""Capability Validator for OniRoute Organization Builder (ACR-005 Phase S2).

Performs deterministic validation on resolved capability reports, checking domain coverage,
duplicates, conflicts, missing capability dependencies, constraint compliance, and evidence completeness.
Does NOT perform AI execution, agent selection, or role assignment.
"""

from __future__ import annotations

from typing import Any

from .capability import Capability, CapabilityConstraint, CapabilityEvidence, CapabilityRequirement


class CapabilityValidator:
    """Deterministic validator for resolved engineering capabilities."""

    def validate_capability_set(
        self,
        capabilities: list[Capability],
        requirements: list[CapabilityRequirement],
        constraints: list[CapabilityConstraint],
        evidence_list: list[CapabilityEvidence],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Validate capability set integrity, coverage, conflicts, and readiness.

        Returns:
            Tuple of (coverage_summary, readiness_summary)
        """
        cap_map: dict[str, Capability] = {cap.capability_id: cap for cap in capabilities}
        cap_ids = set(cap_map.keys())

        # 1. Duplicate check
        duplicates = len(capabilities) - len(cap_ids)

        # 2. Domain coverage breakdown
        domain_counts: dict[str, int] = {}
        for cap in capabilities:
            domain_counts[cap.domain] = domain_counts.get(cap.domain, 0) + 1

        # 3. Requirement coverage check
        covered_reqs = 0
        uncovered_reqs: list[str] = []
        for req in requirements:
            if req.capability_id in cap_ids:
                covered_reqs += 1
            else:
                uncovered_reqs.append(req.requirement_id)

        coverage_ratio = covered_reqs / max(len(requirements), 1)

        coverage_summary: dict[str, Any] = {
            "total_requirements": len(requirements),
            "covered_requirements": covered_reqs,
            "coverage_ratio": round(coverage_ratio, 4),
            "uncovered_requirement_ids": uncovered_reqs,
            "domain_breakdown": domain_counts,
        }

        # 4. Dependency check (missing capabilities)
        missing_dependencies: list[str] = []
        for cap in capabilities:
            for dep_id in cap.dependencies:
                if dep_id not in cap_ids and dep_id not in missing_dependencies:
                    missing_dependencies.append(dep_id)

        # 5. Conflict check
        conflicts: list[str] = []
        local_only_flag = any(c.local_only for c in constraints)
        for c in constraints:
            if local_only_flag and c.allowed_providers and "local" not in [p.lower() for p in c.allowed_providers]:
                conflicts.append(f"Constraint {c.constraint_id}: local_only conflicts with allowed_providers {c.allowed_providers}")

        # 6. Evidence completeness check
        evidence_cap_ids = {e.capability_id for e in evidence_list}
        missing_evidence = [cap_id for cap_id in cap_ids if cap_id not in evidence_cap_ids]

        # 7. Overall Readiness
        is_ready = (
            duplicates == 0
            and len(missing_dependencies) == 0
            and len(conflicts) == 0
            and len(missing_evidence) == 0
            and coverage_ratio >= 0.8
        )

        readiness_summary: dict[str, Any] = {
            "is_ready": is_ready,
            "duplicate_capabilities_count": duplicates,
            "missing_dependencies": missing_dependencies,
            "conflicts": conflicts,
            "missing_evidence": missing_evidence,
            "constraint_violations": len(conflicts),
            "validation_passed": is_ready,
        }

        return coverage_summary, readiness_summary
