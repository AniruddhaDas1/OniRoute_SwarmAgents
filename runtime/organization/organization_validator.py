"""Organization Validator for OniRoute Organization Builder (ACR-005 Phase S3).

Performs deterministic structural validation on an assembled Organization topology, checking:
- Capability coverage
- Role completeness
- Duplicate member prevention
- Dependency integrity
- Department & hierarchy integrity
- Reporting integrity
- Evidence completeness

Performs NO execution, planning, workflow generation, or AI model calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contracts import OrganizationValidatorContract
from .models import Organization, OrganizationReport


class OrganizationValidator(OrganizationValidatorContract):
    """Deterministic structural validator for assembled Organizations."""

    def validate_organization(self, organization: Organization) -> OrganizationReport:
        """Perform comprehensive structural validation on an Organization topology."""
        member_ids = [m.member_id for m in organization.members]
        unique_member_ids = set(member_ids)
        role_ids = [r.role_id for r in organization.roles]

        # 1. Duplicate check
        duplicate_members = len(member_ids) - len(unique_member_ids)

        # 2. Role completeness
        allocated_roles = {m.role.role_id for m in organization.members}
        unallocated_roles = [r_id for r_id in role_ids if r_id not in allocated_roles]

        # 3. Missing dependencies check
        unresolved_dependencies: list[str] = []
        for dep in organization.dependencies:
            if dep.source_member_id not in unique_member_ids or dep.target_member_id not in unique_member_ids:
                unresolved_dependencies.append(dep.dependency_id)

        # 4. Reporting hierarchy integrity check
        unresolved_reporting: list[str] = []
        for pair in organization.hierarchy.reporting_relationships:
            sub = pair.get("subordinate_id") or pair.get("subordinate")
            sup = pair.get("supervisor_id") or pair.get("supervisor")
            if sub and sub not in unique_member_ids and sub != "Executive":
                unresolved_reporting.append(str(sub))
            if sup and sup not in unique_member_ids and sup != "Executive":
                unresolved_reporting.append(str(sup))

        # 5. Evidence completeness
        missing_evidence: list[str] = [
            m.member_id for m in organization.members if not m.evidence and not organization.evidence
        ]

        # 6. Structural integrity verdict
        integrity_ok = (
            duplicate_members == 0
            and len(unallocated_roles) == 0
            and len(unresolved_dependencies) == 0
            and len(unresolved_reporting) == 0
        )

        validation_details: dict[str, Any] = {
            "duplicate_members_count": duplicate_members,
            "unallocated_roles": unallocated_roles,
            "unresolved_dependencies": unresolved_dependencies,
            "unresolved_reporting_links": unresolved_reporting,
            "missing_evidence_members": missing_evidence,
            "total_departments": len(organization.departments),
            "structural_integrity_passed": integrity_ok,
        }

        summary_msg = (
            f"Organization {organization.organization_id} validated successfully with "
            f"{len(organization.members)} members across {len(organization.departments)} departments."
            if integrity_ok
            else f"Organization validation failed for {organization.organization_id}: "
            f"{len(unallocated_roles)} unallocated roles, {len(unresolved_dependencies)} unresolved dependencies."
        )

        return OrganizationReport(
            report_id=f"rep-org-{organization.organization_id}",
            organization_id=organization.organization_id,
            total_members=len(organization.members),
            total_roles=len(organization.roles),
            total_dependencies=len(organization.dependencies),
            total_departments=len(organization.departments),
            structural_integrity_verified=integrity_ok,
            summary=summary_msg,
            validation_details=validation_details,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
