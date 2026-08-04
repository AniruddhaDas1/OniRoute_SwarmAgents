"""Abstract contracts and protocols for Workspace Architecture Foundation (ACR-003 Phase W1).

These declarations define provider-independent boundaries for future resolution,
routing, and workspace management without introducing concrete runtime execution logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .models import (
    ArtifactCategory,
    ArtifactDestination,
    ExecutionContext,
    ProjectMetadata,
    WorkspaceMetadata,
)


class EngineResolverContract(ABC):
    """Abstract interface for resolving Engine Root installation details."""

    @abstractmethod
    def resolve_engine_root(self, candidate_path: Path | None = None) -> Path:
        """Resolve absolute path to installed OniRoute Engine Root."""
        ...

    @abstractmethod
    def is_engine_read_only(self, engine_root: Path) -> bool:
        """Verify Engine Root operational read-only boundary."""
        ...


class WorkspaceResolverContract(ABC):
    """Abstract interface for discovering and resolving Workspace Root."""

    @abstractmethod
    def resolve_workspace(self, cwd: Path, explicit_path: Path | None = None) -> WorkspaceMetadata:
        """Declaratively resolve workspace metadata without modifying disk state."""
        ...


class ArtifactRouterContract(ABC):
    """Abstract interface for routing generated outputs into Workspace Root."""

    @abstractmethod
    def route_artifact(
        self,
        context: ExecutionContext,
        category: ArtifactCategory,
        filename: str,
    ) -> ArtifactDestination:
        """Compute resolved destination path strictly within Workspace Root."""
        ...


class WorkspaceManagerContract(ABC):
    """High-level orchestration contract connecting resolvers, runtime, and router."""

    @abstractmethod
    def create_context(self, cwd: Path, explicit_workspace: Path | None = None) -> ExecutionContext:
        """Assemble ExecutionContext pairing read-only Engine Root with Workspace Root."""
        ...

    @abstractmethod
    def detect_project(self, workspace_root: Path) -> ProjectMetadata:
        """Declaratively identify project type and metadata within workspace."""
        ...
