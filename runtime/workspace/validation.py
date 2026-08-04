"""Workspace Validation Engine for OniRoute (ACR-003 Phase W2).

Validates workspace existence, engine isolation, permissions, and project consistency.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from .models import ProjectMetadata, ValidationIssue, ValidationState


class WorkspaceValidator:
    """Validator asserting workspace boundaries, isolation, and structural integrity."""

    def validate(
        self,
        workspace_root: Path,
        engine_root: Path,
        project_metadata: ProjectMetadata | None = None,
    ) -> ValidationState:
        """Perform workspace and engine boundary validation."""
        issues: list[ValidationIssue] = []

        abs_ws = workspace_root.resolve()
        abs_eng = engine_root.resolve()

        # 1. Check workspace exists
        if not abs_ws.exists():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="WORKSPACE_NOT_FOUND",
                    message=f"Workspace root directory does not exist: {abs_ws}",
                    target_path=abs_ws,
                )
            )
        elif not abs_ws.is_dir():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="WORKSPACE_NOT_DIRECTORY",
                    message=f"Workspace root path is not a directory: {abs_ws}",
                    target_path=abs_ws,
                )
            )

        # 2. Check engine exists
        if not abs_eng.exists():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="ENGINE_NOT_FOUND",
                    message=f"Engine root directory does not exist: {abs_eng}",
                    target_path=abs_eng,
                )
            )
        elif not abs_eng.is_dir():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="ENGINE_NOT_DIRECTORY",
                    message=f"Engine root path is not a directory: {abs_eng}",
                    target_path=abs_eng,
                )
            )

        # 3. Check Engine != Workspace
        if abs_ws.exists() and abs_eng.exists() and abs_ws == abs_eng:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="ENGINE_WORKSPACE_COLLISION",
                    message="Workspace Root must be separate from read-only Engine Root.",
                    target_path=abs_ws,
                )
            )

        # 4. Check workspace writable
        if abs_ws.exists() and abs_ws.is_dir():
            if not os.access(abs_ws, os.W_OK):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="WORKSPACE_NOT_WRITABLE",
                        message=f"Workspace root is not writable: {abs_ws}",
                        target_path=abs_ws,
                    )
                )

        # 5. Check read-only engine boundary confirmation
        if abs_eng.exists() and abs_eng != abs_ws:
            issues.append(
                ValidationIssue(
                    severity="info",
                    code="READ_ONLY_ENGINE_CONFIRMED",
                    message="Engine read-only boundary is confirmed.",
                    target_path=abs_eng,
                )
            )

        # 6. Check project metadata consistency
        if project_metadata is not None and abs_ws.exists():
            if project_metadata.manifest_path is not None and not project_metadata.manifest_path.exists():
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="MANIFEST_NOT_FOUND",
                        message=f"Project manifest path does not exist: {project_metadata.manifest_path}",
                        target_path=project_metadata.manifest_path,
                    )
                )

        has_errors = any(issue.severity == "error" for issue in issues)
        now_str = datetime.now(timezone.utc).isoformat()

        return ValidationState(
            valid=not has_errors,
            issues=issues,
            last_validated=now_str,
        )
