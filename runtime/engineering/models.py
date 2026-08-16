"""Autonomous Engineering Worker Data Contracts (Phase P5.E1 & Phase E1.4)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class TaskState(StrEnum):
    """Deterministic lifecycle state for InvocationTask execution."""

    QUEUED = "Queued"
    READY = "Ready"
    RUNNING = "Running"
    WAITING = "Waiting"
    COMPLETED = "Completed"
    FAILED = "Failed"
    BLOCKED = "Blocked"
    SKIPPED = "Skipped"
    CANCELLED = "Cancelled"


class TaskContext(BaseModel):
    """Immutable, self-describing ExecutionContext bound to an InvocationTask."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(default="msn-default", description="Associated mission identifier")
    workspace_id: str = Field(default="ws-default", description="Target workspace identifier")
    blueprint_id: str = Field(default="blp-default", description="Project blueprint identifier")
    engineering_contract_id: str = Field(..., description="Parent EngineeringContract ID")
    execution_batch_id: str = Field(..., description="Parent ExecutionBatch ID")
    invocation_task_id: str = Field(..., description="Associated InvocationTask ID")
    agent_profile_id: str = Field(default="profile-eng-default", description="Assigned Agent Profile ID")
    skill_bundle_id: str = Field(default="bundle-default", description="Assigned Skill Bundle ID")
    repository_context: Dict[str, Any] = Field(default_factory=dict, description="Repository intelligence and file context")
    execution_constraints: Dict[str, Any] = Field(default_factory=dict, description="Execution and architecture rules")
    execution_priority: str = Field(default="P1_HIGH", description="Execution priority")


class InvocationTask(BaseModel):
    """Immutable single unit of work within an ExecutionBatch."""

    model_config = ConfigDict(frozen=True)

    task_id: str = Field(..., description="Unique invocation task identifier (task-xxxxxx)")
    contract_id: str = Field(..., description="Associated EngineeringContract ID")
    target_path: str = Field(..., description="Target file path for task generation")
    task_type: str = Field(default="implementation", description="Task type (interface, implementation, documentation, test)")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs that must be completed prior to this task")
    execution_order: int = Field(default=1, description="Deterministic execution sequence order index")
    required_capabilities: List[str] = Field(default_factory=list, description="Provider capabilities required")
    preferred_provider: str | None = Field(default=None, description="Preferred provider identifier")
    local_preference: bool = Field(default=True, description="Preference for local execution")
    expected_artifacts: List[str] = Field(default_factory=list, description="Expected output artifact relative paths")
    execution_context: TaskContext | None = Field(default=None, description="Self-describing execution metadata context")
    state: TaskState = Field(default=TaskState.QUEUED, description="Current deterministic execution state")

    def transition_to(self, new_state: TaskState) -> InvocationTask:
        """Validate state transition and return new InvocationTask copy."""
        terminal_states = {TaskState.COMPLETED, TaskState.FAILED, TaskState.BLOCKED, TaskState.SKIPPED, TaskState.CANCELLED}
        if self.state in terminal_states:
            raise ValueError(f"Terminal task state '{self.state}' cannot transition to '{new_state}'.")

        allowed_transitions = {
            TaskState.QUEUED: {TaskState.READY, TaskState.BLOCKED, TaskState.CANCELLED},
            TaskState.READY: {TaskState.RUNNING, TaskState.WAITING, TaskState.CANCELLED},
            TaskState.RUNNING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.WAITING, TaskState.CANCELLED},
            TaskState.WAITING: {TaskState.RUNNING, TaskState.FAILED, TaskState.CANCELLED},
        }

        if new_state not in allowed_transitions.get(self.state, set()):
            raise ValueError(f"Invalid state transition from '{self.state}' to '{new_state}'.")

        return self.model_copy(update={"state": new_state})


class ExecutionBatch(BaseModel):
    """Immutable batch of ordered InvocationTasks generated for an EngineeringContract."""

    model_config = ConfigDict(frozen=True)

    batch_id: str = Field(..., description="Unique execution batch identifier (batch-xxxxxx)")
    contract_id: str = Field(..., description="Associated EngineeringContract ID")
    tasks: List[InvocationTask] = Field(default_factory=list, description="Ordered list of InvocationTasks")
    execution_mode: str = Field(default="sequential", description="Execution strategy (sequential, parallel)")
    timestamp: str = Field(..., description="ISO-8601 creation timestamp")


class EngineeringFailure(BaseModel):
    """Immutable record of an invocation task failure."""

    model_config = ConfigDict(frozen=True)

    task_id: str = Field(..., description="Failed InvocationTask ID")
    contract_id: str = Field(..., description="Associated EngineeringContract ID")
    error_message: str = Field(..., description="Failure details or error message")
    timestamp: str = Field(..., description="ISO-8601 failure timestamp")


class BatchResult(BaseModel):
    """Immutable result of an ExecutionBatch run."""

    model_config = ConfigDict(frozen=True)

    batch_id: str = Field(..., description="Associated ExecutionBatch ID")
    contract_id: str = Field(..., description="Associated EngineeringContract ID")
    task_results: Dict[str, Any] = Field(default_factory=dict, description="Map of task_id to invocation metadata/content")
    failures: List[EngineeringFailure] = Field(default_factory=list, description="List of recorded task failures")
    blocked_tasks: List[str] = Field(default_factory=list, description="List of task IDs blocked by preceding failures")
    timestamp: str = Field(..., description="ISO-8601 completion timestamp")


class EngineeringResult(BaseModel):
    """Immutable Engineering Result contract produced by EngineeringWorkerEngine."""

    model_config = ConfigDict(frozen=True)

    result_id: str = Field(..., description="Unique engineering execution result ID (engres-xxxxxx)")
    contract_id: str = Field(..., description="Associated EngineeringContract ID (ctr-xxxxxx)")
    profile_id: str = Field(..., description="Assigned Agent Profile ID")
    modified_files: List[str] = Field(default_factory=list, description="List of relative paths of modified files")
    created_files: List[str] = Field(default_factory=list, description="List of relative paths of created files")
    artifacts: List[str] = Field(default_factory=list, description="List of generated implementation artifact paths")
    execution_time_ms: float = Field(..., description="Execution duration in milliseconds")
    provider: str = Field(default="oniroute-local-engine", description="AI/LLM provider used for generation")
    model: str = Field(default="gemini-2.5-pro", description="AI/LLM model used for generation")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics (prompt, completion, total)")
    cost_usd: float = Field(default=0.0, description="Estimated execution cost in USD")
    trace_references: List[str] = Field(default_factory=list, description="Trace IDs recorded during execution")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence, performance metrics, and safety checks")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    result_hash: str = Field(..., description="SHA-256 hash of engineering result payload")


class EngineeringCertificationReport(BaseModel):
    """Immutable Engineering Certification Report contract produced by AutonomousEngineeringCertificationEngine."""

    model_config = ConfigDict(frozen=True)

    certification_id: str = Field(..., description="Unique certification identifier (cert-eng-xxxxxx)")
    mission_id: str = Field(..., description="Associated mission identifier")
    pipeline_version: str = Field(default="v1.2", description="Autonomous Engineering Pipeline version")
    contract_versions: Dict[str, str] = Field(default_factory=dict, description="Versions of upstream contract schemas")
    engineering_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of engineering worker execution")
    quality_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of quality gate cross-agent review")
    repair_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of self-healing repair execution")
    verification_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of verification engine checks")
    acceptance_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of acceptance criteria and verdict")
    coverage_summary: Dict[str, Any] = Field(default_factory=dict, description="Code coverage statistics")
    security_summary: Dict[str, Any] = Field(default_factory=dict, description="Security gate audit summary")
    performance_summary: Dict[str, Any] = Field(default_factory=dict, description="End-to-end performance and latency summary")
    production_readiness: bool = Field(..., description="True if complete pipeline is certified production-ready")
    regression_status: str = Field(default="PASSED", description="Regression test suite status")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Audit evidence log and verification hashes")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    certification_hash: str = Field(..., description="SHA-256 hash of certification report payload")
