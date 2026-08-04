from pathlib import Path

from .core_models import MetadataRecord, RepositoryRegistry


class RegistryBuilder:
    def __init__(self, root: Path):
        self.registry = RepositoryRegistry(root=root)

    def register(self, record: MetadataRecord) -> None:
        collection_name = {
            "agent": "agents", "sub_agent": "sub_agents", "skill": "skills",
            "workflow": "workflows", "knowledge": "knowledge_sources",
            "package": "packages", "mapping": "mappings", "registry": "registry_records",
        }[record.kind]
        collection = getattr(self.registry, collection_name)
        if record.id in collection:
            key = f"{record.kind}:{record.id}"
            self.registry.duplicates.setdefault(key, [collection[record.id].path]).append(record.path)
            return
        collection[record.id] = record
