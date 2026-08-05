"""Mission evidence schemas for OniRoute Mission Orchestrator (ACR-004 Phase O1).

Every orchestration decision records immutable evidence across all pipeline stages.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class MissionEvidence(BaseModel):
    """Immutable audit trail of evidence collected across all mission stages."""

    workspace: dict[str, Any] = Field(default_factory=dict, description="Workspace discovery & boundary evidence")
    project: dict[str, Any] = Field(default_factory=dict, description="Project detection & framework metadata evidence")
    requirements: dict[str, Any] = Field(default_factory=dict, description="Parsed user intent & requirement specs evidence")
    constraints: dict[str, Any] = Field(default_factory=dict, description="Resource limits & policy constraint evidence")
    context: dict[str, Any] = Field(default_factory=dict, description="Context Engine snapshot evidence")
    optimization: dict[str, Any] = Field(default_factory=dict, description="ICOE optimization trace evidence")
    planning: dict[str, Any] = Field(default_factory=dict, description="Planning Engine execution plan evidence")
    governance: dict[str, Any] = Field(default_factory=dict, description="Governance policy audit evidence")
    model_selection: dict[str, Any] = Field(default_factory=dict, description="UMAL model selection decision evidence")
    execution: dict[str, Any] = Field(default_factory=dict, description="Invocation & runtime telemetry evidence")
    artifacts: list[dict[str, Any]] = Field(default_factory=list, description="Artifact Router destination evidence")

    def record_stage(self, stage: str, data: dict[str, Any]) -> MissionEvidence:
        """Return a new MissionEvidence instance with updated stage evidence (immutable update)."""
        current_data = self.model_dump(mode="python")
        if stage == "artifacts":
            existing = list(current_data.get("artifacts", []))
            existing.append(data)
            current_data["artifacts"] = existing
        elif stage in current_data:
            merged = dict(current_data[stage])
            merged.update(data)
            current_data[stage] = merged
        else:
            current_data[stage] = data
        return MissionEvidence(**current_data)
