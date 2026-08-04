from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ContextKind = Literal["workflow", "agent", "skill", "artifact", "decision", "approval", "repository", "execution"]


class ContextObject(BaseModel):
    model_config = ConfigDict(frozen=True)
    context_id: str
    kind: ContextKind
    subject_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    relationships: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    priority: int = 50
    scope: tuple[str, ...] = ()
    sensitive_fields: tuple[str, ...] = ()

    @property
    def estimated_size(self) -> int:
        return len(self.model_dump_json())


class WorkflowContext(ContextObject): kind: Literal["workflow"] = "workflow"
class AgentContext(ContextObject): kind: Literal["agent"] = "agent"
class SkillContext(ContextObject): kind: Literal["skill"] = "skill"
class ArtifactContext(ContextObject): kind: Literal["artifact"] = "artifact"
class DecisionContext(ContextObject): kind: Literal["decision"] = "decision"
class ApprovalContext(ContextObject): kind: Literal["approval"] = "approval"
class RepositoryContext(ContextObject): kind: Literal["repository"] = "repository"
class ExecutionContext(ContextObject): kind: Literal["execution"] = "execution"


class RouteStep(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: str
    target: str
    relationship: str


class RoutingPlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    workflow_id: str
    steps: tuple[RouteStep, ...]
    unresolved: tuple[str, ...] = ()
