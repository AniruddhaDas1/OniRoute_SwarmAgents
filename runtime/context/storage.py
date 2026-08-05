from __future__ import annotations

import json
from pathlib import Path

from runtime.workspace import WorkspaceMetadata, WorkspaceStorage, assert_no_engine_write

from .models import ContextObject


class InMemoryContextStorage:
    def __init__(self): self._contexts: dict[str, ContextObject] = {}
    def put(self, context: ContextObject) -> None: self._contexts[context.context_id] = context
    def get(self, context_id: str) -> ContextObject | None: return self._contexts.get(context_id)
    def list_contexts(self) -> tuple[ContextObject, ...]: return tuple(self._contexts.values())
    def remove(self, context_id: str) -> None: self._contexts.pop(context_id, None)
    def clear(self) -> None: self._contexts.clear()
    def count(self) -> int: return len(self._contexts)


class WorkspaceContextStorage:
    """Workspace-local persistence for :class:`ContextObject` snapshots.

    Persists each context as ``<context_id>.json`` in ``.oniroute/context/``.
    Engine Root is never written.
    """

    def __init__(self, workspace_metadata: WorkspaceMetadata) -> None:
        self._metadata = workspace_metadata
        self._storage = WorkspaceStorage(workspace_metadata)

    @property
    def context_root(self) -> Path:
        return self._storage.context_root

    def put(self, context: ContextObject) -> Path:
        """Persist a context snapshot to ``.oniroute/context/``."""
        target_dir = self._storage.ensure_dir("context")
        safe_id = context.context_id.replace(":", "_")
        target = target_dir / f"{safe_id}.json"
        assert_no_engine_write(
            target,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        with target.open("w", encoding="utf-8") as fh:
            json.dump(context.model_dump(mode="json"), fh, indent=2, default=str)
        return target

    def get(self, context_id: str) -> ContextObject | None:
        """Load a context snapshot by ID."""
        safe_id = context_id.replace(":", "_")
        target = self.context_root / f"{safe_id}.json"
        if not target.is_file():
            return None
        with target.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return ContextObject(**data)

    def list_contexts(self) -> list[ContextObject]:
        """List all persisted context snapshots."""
        if not self.context_root.is_dir():
            return []
        contexts: list[ContextObject] = []
        for path in sorted(self.context_root.glob("*.json")):
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            contexts.append(ContextObject(**data))
        return contexts

    def count(self) -> int:
        """Count persisted context snapshots."""
        if not self.context_root.is_dir():
            return 0
        return sum(1 for _ in self.context_root.glob("*.json"))
