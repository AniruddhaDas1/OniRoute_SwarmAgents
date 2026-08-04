from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MetadataRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    kind: Literal["agent", "sub_agent", "skill", "workflow", "knowledge", "package", "mapping", "registry"]
    path: Path
    data: dict[str, Any]


class RepositoryRegistry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    root: Path
    agents: dict[str, MetadataRecord] = Field(default_factory=dict)
    sub_agents: dict[str, MetadataRecord] = Field(default_factory=dict)
    skills: dict[str, MetadataRecord] = Field(default_factory=dict)
    workflows: dict[str, MetadataRecord] = Field(default_factory=dict)
    knowledge_sources: dict[str, MetadataRecord] = Field(default_factory=dict)
    packages: dict[str, MetadataRecord] = Field(default_factory=dict)
    mappings: dict[str, MetadataRecord] = Field(default_factory=dict)
    registry_records: dict[str, MetadataRecord] = Field(default_factory=dict)
    duplicates: dict[str, list[Path]] = Field(default_factory=dict)

    def statistics(self) -> dict[str, int]:
        return {name: len(getattr(self, name)) for name in ("agents", "sub_agents", "skills", "workflows", "knowledge_sources", "packages", "mappings", "registry_records")}


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    path: Path | None = None


class ValidationReport(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list)
    @property
    def valid(self) -> bool: return not any(issue.severity == "error" for issue in self.issues)
    @property
    def errors(self) -> list[ValidationIssue]: return [issue for issue in self.issues if issue.severity == "error"]
    @property
    def warnings(self) -> list[ValidationIssue]: return [issue for issue in self.issues if issue.severity == "warning"]
