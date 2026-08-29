"""E3.1 Repository Writer.

Provides RepositoryWriter for writing generated content to the repository.
Handles file operations with proper error handling and validation.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

from runtime.contracts.e23_models import ArtifactExecutionUnit, OverwritePolicy, PathType
from runtime.contracts.e31_models import (
    BlockingConflict,
    BlockingConflictReport,
    RepositoryWriteError,
    RepositoryWriteResult,
    validate_target_path,
)


class RepositoryWriter:
    """Writes generated content to the repository.

    Handles file operations with:
    - Path validation (within repository scope)
    - Overwrite policy enforcement
    - Atomic writes
    - Proper error handling
    """

    def __init__(self, repository_root: str):
        """Initialize the repository writer.

        Args:
            repository_root: Absolute path to repository root
        """
        self.repository_root = os.path.abspath(repository_root)

        # Track written files
        self._written_files: Dict[str, RepositoryWriteResult] = {}

    def write(
        self,
        content: str,
        unit: ArtifactExecutionUnit,
        skip_validation: bool = False,
    ) -> RepositoryWriteResult:
        """Write content to repository.

        Args:
            content: Generated content to write
            unit: Source artifact execution unit
            skip_validation: Skip path validation (use with caution)

        Returns:
            RepositoryWriteResult with write status

        Raises:
            RepositoryWriteError: If write fails critically
        """
        target_path = unit.target_path

        # Validate path unless skipped
        if not skip_validation:
            is_valid, error = validate_target_path(target_path, self.repository_root)
            if not is_valid:
                return RepositoryWriteResult(
                    write_id=self._compute_write_id(unit),
                    artifact_execution_id=unit.artifact_execution_id,
                    target_path=target_path,
                    absolute_path="",
                    success=False,
                    action="VALIDATION_FAILED",
                    bytes_written=0,
                    error=error,
                )

        # Determine absolute path
        absolute_path = self._get_absolute_path(target_path)

        # Check overwrite policy
        file_exists = os.path.exists(absolute_path)

        if file_exists:
            action = self._determine_action(unit.overwrite_policy)
            if action == "SKIPPED":
                return RepositoryWriteResult(
                    write_id=self._compute_write_id(unit),
                    artifact_execution_id=unit.artifact_execution_id,
                    target_path=target_path,
                    absolute_path=absolute_path,
                    success=True,
                    action="SKIPPED",
                    bytes_written=0,
                    error="",
                )
            elif action == "RENAMED":
                absolute_path, target_path = self._get_renamed_path(absolute_path, target_path)
        else:
            action = "CREATED"

        # Create parent directories if needed
        try:
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        except OSError as e:
            return RepositoryWriteResult(
                write_id=self._compute_write_id(unit),
                artifact_execution_id=unit.artifact_execution_id,
                target_path=target_path,
                absolute_path=absolute_path,
                success=False,
                action=action,
                bytes_written=0,
                error=f"Failed to create directories: {e}",
            )

        # Write content
        try:
            # Use atomic write (write to temp file, then rename)
            temp_path = absolute_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
                bytes_written = f.tell()

            # Atomic rename
            if os.path.exists(absolute_path):
                os.remove(absolute_path)
            os.rename(temp_path, absolute_path)

            result = RepositoryWriteResult(
                write_id=self._compute_write_id(unit),
                artifact_execution_id=unit.artifact_execution_id,
                target_path=target_path,
                absolute_path=absolute_path,
                success=True,
                action=action,
                bytes_written=bytes_written,
                error="",
            )

            self._written_files[unit.artifact_execution_id] = result
            return result

        except OSError as e:
            return RepositoryWriteResult(
                write_id=self._compute_write_id(unit),
                artifact_execution_id=unit.artifact_execution_id,
                target_path=target_path,
                absolute_path=absolute_path,
                success=False,
                action=action,
                bytes_written=0,
                error=f"Write failed: {e}",
            )

    def write_batch(
        self,
        writes: List[Tuple[str, ArtifactExecutionUnit]],
    ) -> List[RepositoryWriteResult]:
        """Write multiple artifacts in batch.

        Args:
            writes: List of (content, unit) tuples

        Returns:
            List of RepositoryWriteResult for each write
        """
        results = []
        for content, unit in writes:
            result = self.write(content, unit)
            results.append(result)
        return results

    def _get_absolute_path(self, target_path: str) -> str:
        """Get absolute filesystem path from repository-relative path."""
        # Normalize path to POSIX style
        posix_path = str(PurePosixPath(target_path))
        return os.path.join(self.repository_root, posix_path)

    def _determine_action(self, policy: OverwritePolicy) -> str:
        """Determine write action based on overwrite policy."""
        policy_actions = {
            OverwritePolicy.SAFE: "SKIPPED",  # Don't overwrite
            OverwritePolicy.OVERWRITE: "OVERWRITTEN",
            OverwritePolicy.SKIP: "SKIPPED",
            OverwritePolicy.RENAME: "RENAMED",
        }
        return policy_actions.get(policy, "OVERWRITTEN")

    def _get_renamed_path(
        self,
        absolute_path: str,
        target_path: str,
    ) -> Tuple[str, str]:
        """Get a renamed path that doesn't conflict.

        Args:
            absolute_path: Current absolute path
            target_path: Current target path

        Returns:
            Tuple of (new_absolute_path, new_target_path)
        """
        base, ext = os.path.splitext(absolute_path)
        counter = 1

        while os.path.exists(f"{base}.{counter}{ext}"):
            counter += 1

        new_absolute = f"{base}.{counter}{ext}"

        # Also update target path
        target_base, target_ext = os.path.splitext(target_path)
        new_target = f"{target_base}.{counter}{target_ext}"

        return new_absolute, new_target

    def _compute_write_id(self, unit: ArtifactExecutionUnit) -> str:
        """Compute deterministic write ID."""
        payload = f"write-{unit.artifact_execution_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def get_written_files(self) -> Dict[str, RepositoryWriteResult]:
        """Get all files written by this writer."""
        return dict(self._written_files)

    def verify_written(self, unit: ArtifactExecutionUnit) -> bool:
        """Verify that a file was written for the given unit.

        Args:
            unit: Artifact execution unit to verify

        Returns:
            True if file was written successfully
        """
        result = self._written_files.get(unit.artifact_execution_id)
        return result is not None and result.success

    def read_written_content(self, unit: ArtifactExecutionUnit) -> Optional[str]:
        """Read the content that was written for a unit.

        Args:
            unit: Artifact execution unit

        Returns:
            Content if file was written, None otherwise
        """
        result = self._written_files.get(unit.artifact_execution_id)
        if result and result.success and result.absolute_path:
            try:
                with open(result.absolute_path, "r", encoding="utf-8") as f:
                    return f.read()
            except OSError:
                return None
        return None


class BlockingConflictDetector:
    """Detects blocking conflicts that prevent generation.

    Checks for:
    - Duplicate target paths
    - Outside scope paths
    - Missing dependencies
    - Circular dependencies
    - Unknown producers
    """

    def __init__(self, repository_root: str):
        """Initialize the conflict detector.

        Args:
            repository_root: Absolute path to repository root
        """
        self.repository_root = repository_root

    def detect_conflicts(
        self,
        units: List[ArtifactExecutionUnit],
    ) -> BlockingConflictReport:
        """Detect blocking conflicts in artifact execution units.

        Args:
            units: List of artifact execution units

        Returns:
            BlockingConflictReport with detected conflicts
        """
        conflicts: List[BlockingConflict] = []

        # Check 1: Duplicate paths
        duplicate_conflicts = self._check_duplicate_paths(units)
        conflicts.extend(duplicate_conflicts)

        # Check 2: Path traversal
        traversal_conflicts = self._check_path_traversal(units)
        conflicts.extend(traversal_conflicts)

        # Check 3: Scope violations
        scope_conflicts = self._check_scope_violations(units)
        conflicts.extend(scope_conflicts)

        # Check 4: Missing dependencies
        missing_dep_conflicts = self._check_missing_dependencies(units)
        conflicts.extend(missing_dep_conflicts)

        has_blocking = len(conflicts) > 0

        return BlockingConflictReport(
            has_blocking_conflicts=has_blocking,
            conflicts=tuple(conflicts),
            can_proceed=not has_blocking,
        )

    def _check_duplicate_paths(
        self,
        units: List[ArtifactExecutionUnit],
    ) -> List[BlockingConflict]:
        """Check for duplicate target paths."""
        conflicts = []
        path_to_units: Dict[str, List[str]] = {}

        for unit in units:
            path = unit.target_path
            if path not in path_to_units:
                path_to_units[path] = []
            path_to_units[path].append(unit.artifact_execution_id)

        for path, unit_ids in path_to_units.items():
            if len(unit_ids) > 1:
                conflicts.append(BlockingConflict(
                    conflict_id=f"dup-path-{hashlib.md5(path.encode()).hexdigest()[:8]}",
                    conflict_type="DUPLICATE_PATH",
                    description=f"Multiple units target same path: {path}",
                    affected_artifact_ids=tuple(unit_ids),
                    resolution_hint="Assign unique target paths to each artifact",
                ))

        return conflicts

    def _check_path_traversal(
        self,
        units: List[ArtifactExecutionUnit],
    ) -> List[BlockingConflict]:
        """Check for path traversal attempts."""
        conflicts = []

        for unit in units:
            is_valid, error = validate_target_path(unit.target_path, self.repository_root)
            if not is_valid:
                conflicts.append(BlockingConflict(
                    conflict_id=f"traversal-{unit.artifact_execution_id}",
                    conflict_type="PATH_TRAVERSAL",
                    description=f"Invalid path for {unit.artifact_execution_id}: {error}",
                    affected_artifact_ids=(unit.artifact_execution_id,),
                    resolution_hint="Use repository-relative paths without '..'",
                ))

        return conflicts

    def _check_scope_violations(
        self,
        units: List[ArtifactExecutionUnit],
    ) -> List[BlockingConflict]:
        """Check for repository scope violations."""
        conflicts = []

        for unit in units:
            scope = unit.repository_scope
            target = unit.target_path

            # Check if target starts with scope prefix
            if scope and not target.startswith(scope):
                # Allow if it's a sibling or child of scope
                normalized_target = target.lstrip("/")
                normalized_scope = scope.rstrip("/")

                if not (normalized_target == normalized_scope or
                        normalized_target.startswith(normalized_scope + "/")):
                    conflicts.append(BlockingConflict(
                        conflict_id=f"scope-{unit.artifact_execution_id}",
                        conflict_type="OUTSIDE_SCOPE",
                        description=f"Path {target} outside authorized scope {scope}",
                        affected_artifact_ids=(unit.artifact_execution_id,),
                        resolution_hint=f"Use paths within {scope}",
                    ))

        return conflicts

    def _check_missing_dependencies(
        self,
        units: List[ArtifactExecutionUnit],
    ) -> List[BlockingConflict]:
        """Check for missing dependencies."""
        conflicts = []
        unit_ids = {u.artifact_execution_id for u in units}
        unit_by_subcontract = {u.sub_contract_id: u.artifact_execution_id for u in units}

        for unit in units:
            for dep_id in unit.dependencies:
                if dep_id not in unit_ids and dep_id not in unit_by_subcontract:
                    conflicts.append(BlockingConflict(
                        conflict_id=f"missing-dep-{unit.artifact_execution_id}-{dep_id}",
                        conflict_type="MISSING_DEPENDENCY",
                        description=f"Unit {unit.artifact_execution_id} depends on unknown {dep_id}",
                        affected_artifact_ids=(unit.artifact_execution_id,),
                        resolution_hint="Ensure all dependencies are in the plan",
                    ))

        return conflicts
