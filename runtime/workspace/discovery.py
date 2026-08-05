"""Deterministic Workspace Discovery engine for OniRoute (ACR-003 Phase W2).

Discovers and resolves Workspace Root using 4-level priority rules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .contracts import WorkspaceResolverContract
from .engine import EngineResolver
from .models import (
    DiscoveryPriority,
    ProjectType,
    TrustLevel,
    WorkspaceLifecycle,
    WorkspaceMetadata,
    WorkspaceStatus,
)
from .project import ProjectDetector
from .validation import WorkspaceValidator

_ONIROUTE_BASENAME = ".oniroute"


class WorkspaceResolver(WorkspaceResolverContract):
    """Deterministic workspace discovery resolver using priority rules."""

    MANIFEST_NAMES = (
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "pubspec.yaml",
        "angular.json",
        "vue.config.js",
        "next.config.js",
        ".oniroute",
        ".git",
    )

    def __init__(
        self,
        engine_resolver: EngineResolver | None = None,
        project_detector: ProjectDetector | None = None,
        validator: WorkspaceValidator | None = None,
    ) -> None:
        self.engine_resolver = engine_resolver or EngineResolver()
        self.project_detector = project_detector or ProjectDetector()
        self.validator = validator or WorkspaceValidator()

    def resolve_workspace(self, cwd: Path, explicit_path: Path | None = None) -> WorkspaceMetadata:
        """Declaratively resolve workspace metadata without modifying disk state."""
        abs_cwd = cwd.resolve()
        engine_root = self.engine_resolver.resolve_engine_root(explicit_path or abs_cwd)

        workspace_root, discovery_priority, discovery_source, confidence = self._discover_root(abs_cwd, explicit_path)

        project_metadata = self.project_detector.detect_project(workspace_root)
        validation_state = self.validator.validate(workspace_root, engine_root, project_metadata)

        status = WorkspaceStatus.VALID if validation_state.valid else WorkspaceStatus.INVALID

        oniroute_base = workspace_root / _ONIROUTE_BASENAME
        now_str = datetime.now(timezone.utc).isoformat()
        ws_id = f"ws-{abs(hash(str(workspace_root))) % 1000000:06d}"

        return WorkspaceMetadata(
            workspace_id=ws_id,
            name=project_metadata.name or workspace_root.name,
            workspace_root=workspace_root,
            engine_root=engine_root,
            project_type=project_metadata.project_type,
            lifecycle=WorkspaceLifecycle.ACTIVE,
            status=status,
            created=now_str,
            version="1.0.0",
            owner=None,
            artifact_root=oniroute_base / "artifacts",
            session_root=oniroute_base / "sessions",
            logs_root=oniroute_base / "logs",
            memory_root=oniroute_base / "memory",
            configuration_root=oniroute_base / "config",
            plans_root=oniroute_base / "plans",
            history_root=oniroute_base / "history",
            traces_root=oniroute_base / "traces",
            generated_root=oniroute_base / "generated",
            temporary_root=oniroute_base / "temporary",
            reports_root=oniroute_base / "reports",
            approvals_root=oniroute_base / "approvals",
            cache_root=oniroute_base / "cache",
            context_root=oniroute_base / "context",
            knowledge_root=oniroute_base / "knowledge",
            runtime_root=oniroute_base / "runtime",
            locks_root=oniroute_base / "locks",
            validation=validation_state,
            trust=TrustLevel.TRUSTED,
            discovery_method=discovery_priority,
            discovery_source=discovery_source,
            confidence=confidence,
        )

    def _discover_root(
        self, cwd: Path, explicit_path: Path | None
    ) -> tuple[Path, DiscoveryPriority, str, float]:
        """Determine workspace root using priority rules:

        1. Explicit workspace argument
        2. Current Working Directory (if manifest or .oniroute exists)
        3. Parent project discovery (climbing ancestors for manifest)
        4. Existing workspace configuration / fallback to CWD
        """
        # Priority 1: Explicit workspace argument
        if explicit_path is not None:
            exp = explicit_path.resolve()
            return exp, DiscoveryPriority.EXPLICIT_ARGUMENT, "explicit_argument", 1.0

        # Priority 2: Current Working Directory
        if self._has_manifest_or_marker(cwd):
            return cwd, DiscoveryPriority.CURRENT_WORKING_DIRECTORY, "current_working_directory", 1.0

        # Priority 3: Parent project discovery
        parent_root = self._find_parent_project(cwd)
        if parent_root is not None:
            return parent_root, DiscoveryPriority.PARENT_PROJECT_DETECTION, "parent_project_detection", 0.85

        # Priority 4: Default fallback / workspace configuration
        return cwd, DiscoveryPriority.WORKSPACE_CONFIGURATION, "workspace_configuration", 0.50

    def _has_manifest_or_marker(self, path: Path) -> bool:
        """Check if path contains any manifest or project marker file."""
        if not path.is_dir():
            return False
        for name in self.MANIFEST_NAMES:
            if (path / name).exists():
                return True
        return False

    def _find_parent_project(self, start_path: Path) -> Path | None:
        """Search ancestor directories for project manifests."""
        curr = start_path.parent if start_path.is_file() else start_path
        visited: set[Path] = set()

        # Start from parent of start_path
        curr = curr.parent
        while curr not in visited:
            visited.add(curr)
            if self._has_manifest_or_marker(curr):
                return curr
            if curr.parent == curr:
                break
            curr = curr.parent

        return None
