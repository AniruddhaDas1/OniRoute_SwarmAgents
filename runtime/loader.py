from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .exceptions import LoadError
from .models import MetadataRecord, RepositoryRegistry
from .registry import RegistryBuilder


class RepositoryLoader:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    def _yaml(self, path: Path) -> dict[str, Any]:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise LoadError(f"Unable to parse {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise LoadError(f"Expected a YAML mapping in {path}")
        return data

    @staticmethod
    def _fallback_id(path: Path, base: Path) -> str:
        return path.relative_to(base).with_suffix("").as_posix()

    def _load_named(self, builder: RegistryBuilder, base_name: str, filename: str, kind: str, id_keys: tuple[str, ...]) -> None:
        base = self.root / base_name
        if not base.exists():
            return
        for path in sorted(base.rglob(filename)):
            data = self._yaml(path)
            identifier = next((str(data[key]) for key in id_keys if data.get(key)), self._fallback_id(path, base))
            actual_kind = "sub_agent" if kind == "agent" and "subagents" in path.parts else kind
            builder.register(MetadataRecord(id=identifier, kind=actual_kind, path=path, data=data))

    def _load_yaml_tree(self, builder: RegistryBuilder, base_name: str, kind: str) -> None:
        base = self.root / base_name
        if not base.exists():
            return
        for path in sorted(base.rglob("*.yaml")):
            data = self._yaml(path)
            identifier = str(data.get("id") or data.get("source_id") or data.get("package_id") or self._fallback_id(path, base))
            builder.register(MetadataRecord(id=identifier, kind=kind, path=path, data=data))

    def load(self) -> RepositoryRegistry:
        if not self.root.is_dir():
            raise LoadError(f"Repository root does not exist: {self.root}")
        builder = RegistryBuilder(self.root)
        self._load_named(builder, "agents", "agent.yaml", "agent", ("id",))
        self._load_named(builder, "skills", "skill.yaml", "skill", ("id", "skill_id"))
        self._load_named(builder, "workflows", "workflow.yaml", "workflow", ("workflow_id", "id"))
        self._load_yaml_tree(builder, "knowledge", "knowledge")
        self._load_yaml_tree(builder, "packages", "package")
        self._load_yaml_tree(builder, "mappings", "mapping")
        registry_dir = self.root / "workflows" / "registry"
        if registry_dir.exists():
            for path in sorted(registry_dir.glob("*.yaml")):
                data = self._yaml(path)
                builder.register(MetadataRecord(id=path.stem, kind="registry", path=path, data=data))
        return builder.registry
