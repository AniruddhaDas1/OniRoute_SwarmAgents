from __future__ import annotations

from typing import Any

import networkx as nx

from .core_models import MetadataRecord, RepositoryRegistry


class Resolver:
    """Read-only relationship and metadata resolution over a registry."""

    def __init__(self, registry: RepositoryRegistry):
        self.registry = registry
        self._all_records: list[MetadataRecord] = [
            record
            for name in ("agents", "sub_agents", "skills", "workflows", "knowledge_sources", "packages")
            for record in getattr(self.registry, name).values()
        ]
        self.records_map: dict[str, MetadataRecord] = {record.id: record for record in self._all_records}
        self.graph = self._build_graph()

    def _all(self) -> list[MetadataRecord]:
        return self._all_records

    def _record(self, collection: str, identifier: str) -> MetadataRecord | None:
        return getattr(self.registry, collection).get(identifier)

    def find_agent(self, identifier: str) -> MetadataRecord | None:
        return self.registry.agents.get(identifier) or self.registry.sub_agents.get(identifier)

    def find_sub_agent(self, identifier: str) -> MetadataRecord | None:
        return self.registry.sub_agents.get(identifier)

    def find_skill(self, identifier: str) -> MetadataRecord | None:
        return self._record("skills", identifier)

    def find_workflow(self, identifier: str) -> MetadataRecord | None:
        return self._record("workflows", identifier)

    def find_package(self, identifier: str) -> MetadataRecord | None:
        return self._record("packages", identifier)

    def find_source(self, identifier: str) -> MetadataRecord | None:
        return self._record("knowledge_sources", identifier)

    @staticmethod
    def _values(data: dict[str, Any], *keys: str) -> list[str]:
        result: list[str] = []
        for key in keys:
            value = data.get(key, [])
            if isinstance(value, list):
                result.extend(str(item.get("id") if isinstance(item, dict) and item.get("id") else item) for item in value)
            elif value:
                result.append(str(value))
        return result

    def related(self, identifier: str, relationship: str | None = None) -> list[MetadataRecord]:
        if identifier not in self.graph:
            return []
        nodes = self.graph.successors(identifier) if relationship is None else (edge[1] for edge in self.graph.out_edges(identifier, data=True) if edge[2].get("relationship") == relationship)
        return [self.records_map[node] for node in nodes if node in self.records_map]

    def agent_relationships(self, identifier: str) -> dict[str, list[MetadataRecord]]:
        return {kind: self.related(identifier, kind) for kind in ("parent", "child", "collaborator", "dependency", "owned_skill", "owned_workflow", "knowledge_source", "mapping")}

    def workflow_relationships(self, identifier: str) -> dict[str, list[MetadataRecord]]:
        return {kind: self.related(identifier, kind) for kind in ("primary_agent", "primary_sub_agent", "supporting_agent", "required_skill", "dependency", "produced_artifact")}

    def skill_relationships(self, identifier: str) -> dict[str, list[MetadataRecord]]:
        return {kind: self.related(identifier, kind) for kind in ("owner_agent", "owner_sub_agent", "related_skill", "compatible_agent", "compatible_workflow", "knowledge_source", "package")}

    def package_relationships(self, identifier: str) -> dict[str, list[MetadataRecord]]:
        return {kind: self.related(identifier, kind) for kind in ("contained_skill", "contained_workflow", "dependency")}

    def search(self, query: str, field: str | None = None) -> list[MetadataRecord]:
        needle = query.casefold()
        fields = [field] if field else ["id", "name", "display_name", "description", "category", "tags", "owner", "compatible_agents", "compatible_skills", "workflow_id", "skill_id", "package_id", "source_id"]
        return [record for record in self._all() if any(needle in str(record.id if key == "id" else record.data.get(key, "")).casefold() for key in fields)]

    def search_by_tag(self, tag: str) -> list[MetadataRecord]:
        return self.search(tag, "tags")

    def search_by_category(self, category: str) -> list[MetadataRecord]:
        return self.search(category, "category")

    def _build_graph(self) -> nx.MultiDiGraph:
        graph = nx.MultiDiGraph()
        for record in self._all():
            graph.add_node(record.id, kind=record.kind, path=str(record.path))
        records = {record.id: record for record in self._all()}
        for record in self._all():
            data = record.data
            relationships = {
                "parent": ("parent",), "child": ("children",), "collaborator": ("collaborators",),
                "dependency": ("dependencies",), "owned_skill": ("skills", "owned_skills"), "owned_workflow": ("workflows", "owned_workflows"),
                "knowledge_source": ("knowledge_sources",), "mapping": ("mappings",), "required_skill": ("required_skills", "compatible_skills"),
                "produced_artifact": ("produced_artifacts",), "primary_agent": ("entry_agent", "owner"), "primary_sub_agent": ("primary_sub_agent",),
                "supporting_agent": ("supporting_agents",), "owner_agent": ("owner",), "owner_sub_agent": ("owner_sub_agent",),
                "related_skill": ("related_skills",), "compatible_agent": ("compatible_agents",), "compatible_workflow": ("compatible_workflows",),
                "package": ("packages",), "contained_skill": ("contained_skills",), "contained_workflow": ("contained_workflows",),
            }
            for relationship, keys in relationships.items():
                for target in self._values(data, *keys):
                    if target in records and target != record.id:
                        graph.add_edge(record.id, target, relationship=relationship)
        return graph
