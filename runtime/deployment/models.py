"""Immutable Mission Deployment Plan models for OniRoute (Phase P3.A1).

Defines declarative Pydantic schemas for the Mission Deployment Planner without introducing
AI invocation, session creation, or runtime execution logic.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field

from runtime.skills.models import AgentProfile


class WaveNumber(int, Enum):
    """Canonical execution wave numbers."""
    WAVE_1_FOUNDATION = 1
    WAVE_2_CORE_DEVELOPMENT = 2
    WAVE_3_INTEGRATION = 3
    WAVE_4_TESTING = 4
    WAVE_5_REVIEW = 5
    WAVE_6_DELIVERY = 6


class WaveName(str, Enum):
    """Human-readable execution wave titles."""
    FOUNDATION = "Foundation"
    CORE_DEVELOPMENT = "Core Development"
    INTEGRATION = "Integration"
    TESTING = "Testing"
    REVIEW = "Review"
    DELIVERY = "Delivery"


class ExecutionWave(BaseModel):
    """Immutable representation of a deterministic execution wave."""

    model_config = ConfigDict(frozen=True)

    wave_number: int = Field(..., ge=1, le=6, description="1-indexed wave stage number (1-6)")
    name: str = Field(..., description="Canonical wave name")
    description: str = Field(default="", description="Detailed objective of this wave")
    profile_ids: List[str] = Field(default_factory=list, description="IDs of AgentProfiles assigned to execute in this wave")
    parallel_group_ids: List[str] = Field(default_factory=list, description="IDs of parallel execution groups within this wave")
    prerequisite_wave_numbers: List[int] = Field(default_factory=list, description="Prerequisite wave numbers that must complete prior to this wave")
    deliverables: List[str] = Field(default_factory=list, description="Planned deliverables produced during this wave")
    review_gate_ids: List[str] = Field(default_factory=list, description="IDs of review gates attached to this wave")
    approval_gate_ids: List[str] = Field(default_factory=list, description="IDs of approval gates attached to this wave")


class ParallelGroup(BaseModel):
    """Immutable execution group for agents running concurrently within a wave."""

    model_config = ConfigDict(frozen=True)

    group_id: str = Field(..., description="Unique parallel group identifier (e.g., pg-w1-1)")
    wave_number: int = Field(..., description="Associated wave number")
    profile_ids: List[str] = Field(default_factory=list, description="IDs of agent profiles executing concurrently")
    can_execute_parallel: bool = Field(default=True, description="True if profiles can run strictly in parallel")
    description: str = Field(default="", description="Description of parallel workload")


class SequentialDependency(BaseModel):
    """Immutable mapping of sequential profile dependencies."""

    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Target agent profile identifier")
    prerequisite_profile_ids: List[str] = Field(default_factory=list, description="Prerequisite profile IDs")
    wave_number: int = Field(..., description="Associated wave number")


class ReviewGate(BaseModel):
    """Immutable review checkpoint for automated or discipline code inspection."""

    model_config = ConfigDict(frozen=True)

    gate_id: str = Field(..., description="Unique review gate identifier")
    name: str = Field(..., description="Human-readable review gate title")
    wave_number: int = Field(..., description="Wave number after which this review gate executes")
    trigger_profiles: List[str] = Field(default_factory=list, description="Profile IDs whose output triggers this gate")
    review_type: str = Field(..., description="Type of review (e.g. AUTOMATED_TEST, CODE_REVIEW, SECURITY_AUDIT)")
    required_checks: List[str] = Field(default_factory=list, description="Required checks or assertions")
    blocking: bool = Field(default=True, description="Whether failure blocks downstream wave execution")


class ApprovalGate(BaseModel):
    """Immutable formal approval gate requiring sign-off before proceeding."""

    model_config = ConfigDict(frozen=True)

    gate_id: str = Field(..., description="Unique approval gate identifier")
    name: str = Field(..., description="Human-readable approval gate title")
    wave_number: int = Field(..., description="Wave number preceding which sign-off is required")
    required_approver: str = Field(..., description="Role or entity required for approval (e.g. LEAD_ARCHITECT, HUMAN_OPERATOR)")
    criteria: List[str] = Field(default_factory=list, description="Approval criteria")
    status: str = Field(default="PENDING", description="Approval status")
    blocking: bool = Field(default=True, description="Whether pending sign-off blocks downstream wave execution")


class HumanApprovalCheckpoint(BaseModel):
    """Immutable human-in-the-loop approval checkpoint."""

    model_config = ConfigDict(frozen=True)

    checkpoint_id: str = Field(..., description="Unique human approval checkpoint identifier")
    wave_number: int = Field(..., description="Wave number requiring human intervention")
    stage_name: str = Field(..., description="Stage name")
    description: str = Field(..., description="Description of the approval request")
    required: bool = Field(default=True, description="True if human intervention is mandatory")
    approver_role: str = Field(default="HUMAN_OPERATOR", description="Approver role")


class ArtifactRoute(BaseModel):
    """Immutable mapping of artifact flow between upstream producers and downstream consumers."""

    model_config = ConfigDict(frozen=True)

    route_id: str = Field(..., description="Unique artifact route identifier")
    source_profile_id: str = Field(..., description="Upstream producer AgentProfile ID")
    target_profile_id: str = Field(..., description="Downstream consumer AgentProfile ID")
    artifact_name: str = Field(..., description="Name or path pattern of routed artifact")
    source_wave: int = Field(..., description="Source wave number")
    target_wave: int = Field(..., description="Target wave number")


class RetryPolicy(BaseModel):
    """Immutable retry policy for agent execution within waves."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(default=3, description="Maximum retry attempts per profile")
    backoff_factor: float = Field(default=1.5, description="Exponential backoff multiplier")
    retryable_errors: List[str] = Field(
        default_factory=lambda: ["TIMEOUT", "RESOURCE_BUSY", "TRANSIENT_FAILURE"],
        description="Error codes eligible for retry",
    )
    per_profile_overrides: Dict[str, int] = Field(default_factory=dict, description="Max retries override per profile_id")


class FailureHandlingPolicy(BaseModel):
    """Immutable failure handling strategy for swarm execution."""

    model_config = ConfigDict(frozen=True)

    action: str = Field(default="ABORT_MISSION", description="Primary action on unrecoverable failure (ABORT_MISSION, ROLLBACK_WAVE, ISOLATE_PROFILE, HALT_FOR_APPROVAL)")
    max_failure_threshold: int = Field(default=1, description="Maximum profile failures allowed before triggering failure action")
    rollback_on_failure: bool = Field(default=True, description="Whether to trigger rollback on wave failure")
    isolation_enabled: bool = Field(default=True, description="Whether failed profile execution is isolated")


class RollbackPolicy(BaseModel):
    """Immutable rollback strategy for execution recovery."""

    model_config = ConfigDict(frozen=True)

    strategy: str = Field(default="SNAPSHOT_RESTORE", description="Rollback strategy (SNAPSHOT_RESTORE, REVERT_ARTIFACTS, CLEAN_WORKSPACE)")
    checkpoint_enabled: bool = Field(default=True, description="Whether state checkpoints are captured per wave")
    rollback_target_wave: int = Field(default=1, description="Default wave to revert to upon rollback")


class TimeoutPolicy(BaseModel):
    """Immutable timeout rules for total mission, wave, and profile execution."""

    model_config = ConfigDict(frozen=True)

    total_mission_timeout_seconds: int = Field(default=1800, description="Total mission execution timeout in seconds")
    wave_timeouts: Dict[int, int] = Field(default_factory=dict, description="Timeout seconds mapped per wave number (1-6)")
    profile_timeouts: Dict[str, int] = Field(default_factory=dict, description="Timeout seconds mapped per profile_id")


class ExecutionBudgetAllocation(BaseModel):
    """Immutable budget allocation across execution waves and agent profiles."""

    model_config = ConfigDict(frozen=True)

    total_budget_usd: float = Field(default=50.0, description="Total allocated budget in USD")
    wave_budgets: Dict[int, float] = Field(default_factory=dict, description="Budget allocation in USD per wave number")
    profile_budgets: Dict[str, float] = Field(default_factory=dict, description="Budget allocation in USD per profile_id")
    currency: str = Field(default="USD", description="Currency symbol")


class MissionDeploymentPlan(BaseModel):
    """Immutable Mission Deployment Plan.

    Consolidates EngineeringExecutionPlan and AgentProfileReport into a deterministic,
    deployment-ready execution contract without performing execution, creating sessions,
    or invoking AI models.
    """

    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(..., description="Unique deployment plan identifier (dep-xxxxxx)")
    mission_id: str = Field(..., description="Associated mission identifier")
    execution_plan_id: str = Field(..., description="Associated EngineeringExecutionPlan identifier")
    agent_profiles: List[AgentProfile] = Field(default_factory=list, description="All scheduled Agent Profiles")
    execution_waves: List[ExecutionWave] = Field(default_factory=list, description="Ordered execution waves (Waves 1..6)")
    parallel_execution_groups: Dict[str, List[str]] = Field(default_factory=dict, description="Parallel execution mapping wave_id -> profile IDs")
    parallel_groups: List[ParallelGroup] = Field(default_factory=list, description="Detailed parallel execution group records")
    sequential_dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Profile dependency mapping profile_id -> prerequisite IDs")
    review_gates: List[ReviewGate] = Field(default_factory=list, description="Automated and discipline review gates")
    approval_gates: List[ApprovalGate] = Field(default_factory=list, description="Formal approval gates")
    human_approval_checkpoints: List[HumanApprovalCheckpoint] = Field(default_factory=list, description="Human sign-off checkpoints")
    artifact_routes: List[ArtifactRoute] = Field(default_factory=list, description="Artifact flow routes")
    retry_rules: RetryPolicy = Field(..., description="Retry policy")
    failure_handling: FailureHandlingPolicy = Field(..., description="Failure handling policy")
    rollback_strategy: RollbackPolicy = Field(..., description="Rollback policy")
    execution_constraints: List[str] = Field(default_factory=list, description="Consolidated execution constraints")
    budget_allocation: ExecutionBudgetAllocation = Field(..., description="Budget allocation")
    timeout_rules: TimeoutPolicy = Field(..., description="Timeout rules")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Consolidated planning evidence and validation results")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
    deployment_hash: str = Field(..., description="SHA-256 Deployment Hash")
