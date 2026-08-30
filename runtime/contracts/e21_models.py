"""E2.1 Extended Engineering Contract Models.

Provides DeliverableContract, AcceptanceCriteria, and ContractTraceability
models that extend the P4.G4 EngineeringContract data contract layer.
These models are self-contained and do not depend on runtime.contracts.models
to avoid circular imports.
"""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class DeliverableContract(BaseModel):
 """Immutable structured deliverable contract derived from an EngineeringExecutionPlan deliverable."""

 model_config = ConfigDict(frozen=True)

 deliverable_id: str = Field(description="Unique deliverable identifier (del-{contract_id}-{n:02d})")
 contract_id: str = Field(description="Parent EngineeringContract identifier")
 mission_id: str = Field(description="Associated mission identifier")
 description: str = Field(description="WHAT must exist after execution")
 deliverable_type: str = Field(description="Deliverable type (frontend_application, api_endpoint, database_schema, migration, auth_flow, tests, documentation, component, config, shared)")
 acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria for this deliverable")
 verification_method: str = Field(description="Verification method (automated_test, manual_review, lint_check, build_success, integration_test)")
 estimated_complexity: str = Field(description="Estimated complexity (LOW, MEDIUM, HIGH)")
 dependencies: List[str] = Field(default_factory=list, description="Deliverable IDs this depends on")


class AcceptanceCriteria(BaseModel):
 """Immutable acceptance criteria in Given/When/Then format."""

 model_config = ConfigDict(frozen=True)

 criteria_id: str = Field(description="Unique criteria identifier (ac-{contract_id}-{n:02d})")
 contract_id: str = Field(description="Parent EngineeringContract identifier")
 mission_id: str = Field(description="Associated mission identifier")
 description: str = Field(description="Given/When/Then formatted acceptance criteria")
 category: str = Field(description="Criteria category (functional, security, performance, integration, quality)")
 is_deterministic: bool = Field(description="True if criteria is machine-verifiable")
 test_reference: str = Field(default="", description="Optional test file reference for automated verification")


class ContractTraceability(BaseModel):
 """Immutable end-to-end traceability record linking upstream artifacts to an EngineeringContract."""

 model_config = ConfigDict(frozen=True)

 contract_id: str = Field(description="EngineeringContract identifier")
 mission_id: str = Field(description="Associated mission identifier")
 intent_report_id: str = Field(default="", description="Source IntentReport identifier")
 execution_plan_id: str = Field(default="", description="Source EngineeringExecutionPlan identifier")
 skill_bundle_report_id: str = Field(default="", description="Source ExecutionSkillBundleReport identifier")
 agent_profile_report_id: str = Field(default="", description="Source AgentProfileReport identifier")
 allocation_report_id: str = Field(default="", description="Source ImplementationAllocationReport identifier")
 source_deliverable: str = Field(default="", description="Which plan deliverable this contract covers")
 trace_chain: List[str] = Field(default_factory=list, description="Ordered chain of upstream identifiers for full traceability")


class ContractCoverageMetrics(BaseModel):
 """E2.1.11 - Immutable coverage metrics for contract generation validation."""

 model_config = ConfigDict(frozen=True)

 total_bundles: int = Field(description="Total number of ExecutionSkillBundles")
 contracted_bundles: int = Field(description="Number of bundles with contracts")
 coverage_percent: float = Field(description="Coverage percentage (0.0 to 100.0)")
 uncovered_bundles: List[str] = Field(
 default_factory=list,
 description="Bundle IDs without contracts",
 )
 total_deliverables: int = Field(
 description="Total expected deliverables across all bundles",
 )
 covered_deliverables: int = Field(
 description="Number of deliverables covered by contracts",
 )
 uncovered_deliverables: List[str] = Field(
 default_factory=list,
 description="Deliverable descriptions not covered",
 )
 total_disciplines: int = Field(
 description="Total distinct engineering disciplines required",
 )
 represented_disciplines: int = Field(
 description="Number of disciplines represented in contracts",
 )
 missing_disciplines: List[str] = Field(
 default_factory=list,
 description="Disciplines not represented in any contract",
 )


# ---------------------------------------------------------------------------
# E2.1.8 - Repository scope mapping per discipline
# ---------------------------------------------------------------------------
DISCIPLINE_REPOSITORY_SCOPE: Dict[str, str] = {
 "Frontend": "frontend/src/",
 "Backend": "backend/src/",
 "Database": "database/migrations/",
 "Infrastructure": "infrastructure/",
 "Security": "security/",
 "AI": "ai/",
 "Automation": "automation/",
 "Testing": "tests/",
 "Documentation": "docs/",
 "Analytics": "analytics/",
 "DevOps": "devops/",
 "Mobile": "mobile/",
 "Software Engineering": "src/",
 "QA": "tests/",
 "Shared": "shared/",
}

# ---------------------------------------------------------------------------
# E2.1.5 - Deliverable type mapping by discipline
# ---------------------------------------------------------------------------
DISCIPLINE_DELIVERABLE_TYPE: Dict[str, str] = {
 "Frontend": "CODE",
 "Backend": "CODE",
 "Database": "CONFIG",
 "Infrastructure": "INFRASTRUCTURE",
 "Security": "CODE",
 "AI": "CODE",
 "Automation": "CODE",
 "Testing": "TEST",
 "Documentation": "DOCUMENTATION",
 "Analytics": "CODE",
 "DevOps": "INFRASTRUCTURE",
 "Mobile": "CODE",
 "Software Engineering": "CODE",
 "QA": "TEST",
 "Shared": "CODE",
}

# ---------------------------------------------------------------------------
# E2.1.5 - Verification method by deliverable type
# ---------------------------------------------------------------------------
DELIVERABLE_VERIFICATION_METHOD: Dict[str, str] = {
 "CODE": "AUTOMATED_SCAN",
 "CONFIG": "INTEGRATION_TEST",
 "DOCUMENTATION": "MANUAL_REVIEW",
 "TEST": "UNIT_TEST",
 "INFRASTRUCTURE": "INTEGRATION_TEST",
 "ASSET": "MANUAL_REVIEW",
}

# ---------------------------------------------------------------------------
# E2.1.6 - Acceptance criteria templates by category
# ---------------------------------------------------------------------------
ACCEPTANCE_CRITERIA_TEMPLATES: Dict[str, Dict[str, str]] = {
 "FUNCTIONAL": {
 "given": "the {discipline} module is initialized with required inputs",
 "when": "the {objective} is executed",
 "then": "the expected deliverables are produced and pass validation",
 },
 "SECURITY": {
 "given": "all security policies and constraints are defined",
 "when": "the {discipline} implementation is reviewed",
 "then": "no security vulnerabilities or policy violations are detected",
 },
 "PERFORMANCE": {
 "given": "the performance benchmarks are established",
 "when": "the {discipline} workload is executed",
 "then": "all performance expectations are met within defined bounds",
 },
 "COMPLIANCE": {
 "given": "the coding standards and architectural rules are specified",
 "when": "the {discipline} output is audited",
 "then": "all standards and rules are satisfied",
 },
 "QUALITY": {
 "given": "the testing requirements are defined",
 "when": "the test suite is executed against the {discipline} output",
 "then": "all tests pass with 100% success rate",
 },
}

# ---------------------------------------------------------------------------
# E2.1.9 / Priority mapping from SkillPriority to generation_priority format
# ---------------------------------------------------------------------------
SKILL_PRIORITY_TO_GENERATION: Dict[str, str] = {
 "CRITICAL": "P0_CRITICAL",
 "HIGH": "P1_HIGH",
 "MEDIUM": "P2_MEDIUM",
 "LOW": "P3_LOW",
 "OPTIONAL": "P3_LOW",
 "SUPPORT": "P3_LOW",
}

PRIORITY_RANK: Dict[str, int] = {
 "CRITICAL": 0,
 "HIGH": 1,
 "MEDIUM": 2,
 "LOW": 3,
 "OPTIONAL": 4,
 "SUPPORT": 5,
}

