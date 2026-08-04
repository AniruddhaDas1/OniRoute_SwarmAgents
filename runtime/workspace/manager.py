"""Workspace Manager orchestration component for OniRoute (ACR-003 Phase W2).

Coordinates engine resolution, workspace discovery, project detection, and context creation.
"""

from __future__ import annotations

from pathlib import Path

from .contracts import WorkspaceManagerContract
from .discovery import WorkspaceResolver
from .engine import EngineResolver
from .models import ExecutionContext, ProjectMetadata, WorkspaceMetadata
from .project import ProjectDetector
from .validation import WorkspaceValidator


class WorkspaceManager(WorkspaceManagerContract):
    """High-level orchestration contract connecting resolvers, project detection, and context builder."""

    def __init__(
        self,
        engine_resolver: EngineResolver | None = None,
        workspace_resolver: WorkspaceResolver | None = None,
        project_detector: ProjectDetector | None = None,
        validator: WorkspaceValidator | None = None,
    ) -> None:
        self.engine_resolver = engine_resolver or EngineResolver()
        self.project_detector = project_detector or ProjectDetector()
        self.validator = validator or WorkspaceValidator()
        self.workspace_resolver = (
            workspace_resolver
            or WorkspaceResolver(
                engine_resolver=self.engine_resolver,
                project_detector=self.project_detector,
                validator=self.validator,
            )
        )

    def create_context(self, cwd: Path, explicit_workspace: Path | None = None) -> ExecutionContext:
        """Assemble ExecutionContext pairing read-only Engine Root with Workspace Root."""
        abs_cwd = cwd.resolve()
        ws_meta = self.workspace_resolver.resolve_workspace(cwd=abs_cwd, explicit_path=explicit_workspace)
        proj_meta = self.detect_project(ws_meta.workspace_root)

        return ExecutionContext(
            engine_root=ws_meta.engine_root,
            workspace_root=ws_meta.workspace_root,
            cwd=abs_cwd,
            workspace_metadata=ws_meta,
            project_metadata=proj_meta,
            discovery_method=ws_meta.discovery_method,
            discovery_source=ws_meta.discovery_source,
            confidence=ws_meta.confidence,
        )

    def detect_project(self, workspace_root: Path) -> ProjectMetadata:
        """Declaratively identify project type and metadata within workspace."""
        return self.project_detector.detect_project(workspace_root)
