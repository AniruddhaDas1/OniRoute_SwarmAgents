"""Artifact Router for OniRoute Workspace Architecture (ACR-003 Phase W3).

Resolves canonical destinations for generated artifacts strictly within the
Workspace Root, validates ownership boundaries, prevents Engine Root writes,
normalizes paths, creates directories lazily, validates collisions, and
supports future artifact categories through a registered mapping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .contracts import ArtifactRouterContract
from .engine_safety import assert_no_engine_write
from .exceptions import ArtifactCollisionError
from .models import (
    ArtifactCategory,
    ArtifactDestination,
    ExecutionContext,
    WorkspaceMetadata,
)
from .storage import WorkspaceStorage


class ArtifactRouter(ArtifactRouterContract):
    """Concrete artifact router resolving destinations inside the Workspace Root.

    Category → subdirectory mapping is stored in ``CATEGORY_DIR_MAP`` and can
    be extended at runtime via :meth:`register_category` to support future
    artifact categories.

    Collision policy:
    - **lenient** (default): existing files are renamed with a UTC timestamp suffix.
    - **strict**: :class:`ArtifactCollisionError` is raised on collision.
    """

    ONIROUTE_SUBDIR: str = ".oniroute"

    CATEGORY_DIR_MAP: dict[ArtifactCategory, str] = {
        ArtifactCategory.SOURCE_CODE: "generated",
        ArtifactCategory.DOCUMENTATION: "artifacts",
        ArtifactCategory.IMAGES: "artifacts",
        ArtifactCategory.REPORTS: "reports",
        ArtifactCategory.TESTS: "generated",
        ArtifactCategory.PRESENTATIONS: "artifacts",
        ArtifactCategory.ARCHITECTURE: "artifacts",
        ArtifactCategory.LOGS: "logs",
        ArtifactCategory.PLANS: "plans",
        ArtifactCategory.SESSIONS: "sessions",
        ArtifactCategory.TEMPORARY_OUTPUTS: "temporary",
    }

    #: Fallback subdirectory for unknown or future categories.
    DEFAULT_CATEGORY_DIR: str = "artifacts"

    def __init__(
        self,
        workspace_metadata: WorkspaceMetadata | None = None,
        strict_collisions: bool = False,
    ) -> None:
        self._metadata = workspace_metadata
        self._strict_collisions = strict_collisions

    # ── extensibility ─────────────────────────────────────────────────

    def register_category(self, category: ArtifactCategory, directory: str) -> None:
        """Register or override a category → subdirectory mapping."""
        self.CATEGORY_DIR_MAP[category] = directory

    def _resolve_metadata(self, context: ExecutionContext) -> WorkspaceMetadata:
        """Prefer context metadata; fall back to constructor metadata."""
        if context.workspace_metadata is not None:
            return context.workspace_metadata
        if self._metadata is not None:
            return self._metadata
        # Build a minimal metadata from context roots
        return WorkspaceMetadata(
            workspace_id="ws-unknown",
            name=context.workspace_root.name,
            workspace_root=context.workspace_root,
            engine_root=context.engine_root,
            created=datetime.now(timezone.utc).isoformat(),
            artifact_root=context.workspace_root / self.ONIROUTE_SUBDIR / "artifacts",
            session_root=context.workspace_root / self.ONIROUTE_SUBDIR / "sessions",
            logs_root=context.workspace_root / self.ONIROUTE_SUBDIR / "logs",
            memory_root=context.workspace_root / self.ONIROUTE_SUBDIR / "memory",
            configuration_root=context.workspace_root / self.ONIROUTE_SUBDIR / "config",
        )

    def _resolve_subdir(self, category: ArtifactCategory) -> str:
        """Map an artifact category to a subdirectory name."""
        return self.CATEGORY_DIR_MAP.get(category, self.DEFAULT_CATEGORY_DIR)

    def _resolve_collision(
        self, target_dir: Path, filename: str
    ) -> tuple[str, Path]:
        """Return ``(unique_filename, unique_path)`` for *filename* in *target_dir*.

        In strict mode, a collision raises :class:`ArtifactCollisionError`.
        In lenient mode, a UTC-timestamp suffix is inserted before the file
        extension until a unique name is found.
        """
        target_path = target_dir / filename
        if not target_path.exists():
            return filename, target_path

        if self._strict_collisions:
            raise ArtifactCollisionError(
                f"Artifact collision: '{filename}' already exists in '{target_dir}'. "
                f"Strict mode prevents automatic renaming."
            )

        stem = target_path.stem
        suffix = target_path.suffix
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        unique_name = f"{stem}_{ts}{suffix}"
        unique_path = target_dir / unique_name
        counter = 1
        while unique_path.exists():
            unique_name = f"{stem}_{ts}_{counter}{suffix}"
            unique_path = target_dir / unique_name
            counter += 1
        return unique_name, unique_path

    # ── ArtifactRouterContract implementation ──────────────────────────

    def route_artifact(
        self,
        context: ExecutionContext,
        category: ArtifactCategory,
        filename: str,
    ) -> ArtifactDestination:
        """Resolve a destination path strictly within the Workspace Root.

        Steps:
        1. Map *category* → subdirectory (supports future categories).
        2. Create the subdirectory lazily via ``WorkspaceStorage.ensure_dir``.
        3. Compute normalized absolute and relative paths.
        4. Resolve filename collisions.
        5. Assert the destination is inside workspace and outside engine.
        6. Return a validated :class:`ArtifactDestination`.
        """
        metadata = self._resolve_metadata(context)
        storage = WorkspaceStorage(metadata)

        subdir = self._resolve_subdir(category)
        target_dir = storage.ensure_dir(subdir)

        unique_name, unique_path = self._resolve_collision(target_dir, filename)

        # Engine safety: verify the resolved path is within workspace, outside engine
        assert_no_engine_write(
            unique_path,
            metadata.workspace_root,
            metadata.engine_root,
        )

        relative = Path(self.ONIROUTE_SUBDIR) / subdir / unique_name
        absolute = metadata.workspace_root / relative

        destination = ArtifactDestination(
            category=category,
            relative_path=relative,
            absolute_path=absolute,
            workspace_root=metadata.workspace_root,
            engine_root=metadata.engine_root,
            read_only_engine_asserted=True,
        )

        if not destination.validate_boundary():
            raise AssertionError(
                f"ArtifactRouter produced an invalid boundary destination: {absolute}"
            )

        return destination
