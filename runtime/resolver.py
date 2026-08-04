from .models import MetadataRecord, RepositoryRegistry


class Resolver:
    def __init__(self, registry: RepositoryRegistry):
        self.registry = registry

    def find_agent(self, identifier: str) -> MetadataRecord | None:
        return self.registry.agents.get(identifier) or self.registry.sub_agents.get(identifier)

    def find_skill(self, identifier: str) -> MetadataRecord | None:
        return self.registry.skills.get(identifier)

    def find_workflow(self, identifier: str) -> MetadataRecord | None:
        return self.registry.workflows.get(identifier)

    def find_package(self, identifier: str) -> MetadataRecord | None:
        return self.registry.packages.get(identifier)

    def find_source(self, identifier: str) -> MetadataRecord | None:
        return self.registry.knowledge_sources.get(identifier)

    def _search(self, field: str, value: str) -> list[MetadataRecord]:
        value = value.casefold()
        records = [*self.registry.agents.values(), *self.registry.sub_agents.values(), *self.registry.skills.values(), *self.registry.workflows.values(), *self.registry.packages.values(), *self.registry.knowledge_sources.values()]
        return [record for record in records if value in {str(item).casefold() for item in (record.data.get(field) if isinstance(record.data.get(field), list) else [record.data.get(field)])}]

    def search_by_tag(self, tag: str) -> list[MetadataRecord]:
        return self._search("tags", tag)

    def search_by_category(self, category: str) -> list[MetadataRecord]:
        return self._search("category", category)
