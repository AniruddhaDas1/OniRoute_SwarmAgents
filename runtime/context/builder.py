from __future__ import annotations

from typing import Any

from runtime.models import MetadataRecord, RepositoryRegistry
from runtime.resolver import Resolver

from .models import AgentContext, ArtifactContext, ContextObject, ExecutionContext, RepositoryContext, SkillContext, WorkflowContext


class ContextBuilder:
    def __init__(self, registry: RepositoryRegistry, configuration: dict[str, Any] | None = None):
        self.registry = registry
        self.resolver = Resolver(registry)
        self.configuration = configuration or {}

    def _context(self, record: MetadataRecord, cls: type[ContextObject]) -> ContextObject:
        relationships = tuple(sorted({str(edge[1]) for edge in self.resolver.graph.out_edges(record.id, data=True)}))
        artifacts = tuple(str(x) for x in record.data.get("produced_artifacts", []))
        dependencies = tuple(str(x) for x in record.data.get("dependencies", []))
        return cls(context_id=f"{record.kind}:{record.id}", subject_id=record.id, data=dict(sorted(record.data.items())), relationships=relationships, artifacts=artifacts, dependencies=dependencies, provenance=(str(record.path),), scope=(record.kind,))

    def workflow(self, identifier: str) -> WorkflowContext:
        record = self.resolver.find_workflow(identifier)
        if not record: raise KeyError(identifier)
        return self._context(record, WorkflowContext)

    def agent(self, identifier: str) -> AgentContext:
        record = self.resolver.find_agent(identifier)
        if not record: raise KeyError(identifier)
        return self._context(record, AgentContext)

    def skill(self, identifier: str) -> SkillContext:
        record = self.resolver.find_skill(identifier)
        if not record: raise KeyError(identifier)
        return self._context(record, SkillContext)

    def artifact(self, identifier: str, metadata: dict[str, Any] | None = None) -> ArtifactContext:
        return ArtifactContext(context_id=f"artifact:{identifier}", subject_id=identifier, data=metadata or {}, scope=("artifact",))

    def repository(self) -> RepositoryContext:
        return RepositoryContext(context_id="repository:root", subject_id=str(self.registry.root), data={"statistics": self.registry.statistics(), "configuration": self.configuration}, provenance=(str(self.registry.root),), scope=("repository",))

    def execution(self, workflow_id: str) -> ExecutionContext:
        return ExecutionContext(context_id=f"execution:{workflow_id}", subject_id=workflow_id, data={"metadata_only": True, "workflow_id": workflow_id}, scope=("execution-metadata",))

    def build(self, kind: str, identifier: str) -> ContextObject:
        return getattr(self, kind)(identifier)
