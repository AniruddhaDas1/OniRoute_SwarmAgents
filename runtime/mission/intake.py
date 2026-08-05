"""Mission Intake component for OniRoute Mission Orchestrator (ACR-004 Phase O2).

Mission Intake is the single entry point that accepts natural-language CLI requests
and converts them into canonical MissionRequest objects.

Mission Intake MUST NOT perform:
- Planning
- Agent selection
- Skill resolution
- Knowledge resolution
- Workflow generation
- AI execution

It ONLY normalizes user intent and attaches workspace metadata.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.workspace import WorkspaceManager

from .contracts import MissionIntakeContract
from .exceptions import EmptyCommandError, MissionIntakeError, WorkspaceUnavailableError
from .models import MissionRequest
from .states import MissionState


class MissionNormalizer:
    """Deterministic normalizer for natural language command text."""

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize unicode, newlines, tabs, and repeated whitespace.

        Preserves original semantic meaning and casing.
        """
        if not text:
            return ""
        # 1. Unicode NFKC normalization
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Normalize newlines, carriage returns, and tabs to single spaces
        normalized = re.sub(r"[\r\n\t]+", " ", normalized)

        # 3. Collapse multiple consecutive spaces to a single space
        normalized = re.sub(r"\s+", " ", normalized)

        # 4. Strip leading/trailing whitespace
        normalized = normalized.strip()

        return normalized

    @staticmethod
    def extract_structure(normalized_text: str) -> tuple[str, str]:
        """Extract primary command token and remaining instruction."""
        if not normalized_text:
            return "", ""
        parts = normalized_text.split(maxsplit=1)
        primary_command = parts[0]
        instruction = parts[1] if len(parts) > 1 else ""
        return primary_command, instruction


class MissionIntake(MissionIntakeContract):
    """Concrete Mission Intake processor."""

    def __init__(self, workspace_manager: WorkspaceManager | None = None) -> None:
        self.workspace_manager = workspace_manager or WorkspaceManager()

    def process_intake(
        self,
        raw_command: str,
        explicit_workspace: Path | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> MissionRequest:
        """Receive a raw command string and convert it into a canonical MissionRequest.

        Does NOT perform planning, workflow generation, or AI execution.
        """
        if not raw_command or not raw_command.strip():
            raise EmptyCommandError("Mission command cannot be empty or whitespace-only.")

        if explicit_workspace is not None:
            exp_path = Path(explicit_workspace)
            if not exp_path.exists():
                raise WorkspaceUnavailableError(
                    f"Specified workspace path '{exp_path}' does not exist."
                )

        normalized = MissionNormalizer.normalize(raw_command)
        if not normalized:
            raise EmptyCommandError("Mission command cannot be empty after normalization.")

        primary_cmd, instruction = MissionNormalizer.extract_structure(normalized)

        # Resolve workspace context and attach metadata
        cwd = Path.cwd()
        ctx = self.workspace_manager.create_context(
            cwd=cwd, explicit_workspace=explicit_workspace
        )

        ws_meta_snapshot = None
        if ctx.workspace_metadata is not None:
            ws_meta_snapshot = ctx.workspace_metadata.model_dump(mode="json")

        now_str = datetime.now(timezone.utc).isoformat()
        hash_id = abs(hash(f"{raw_command}:{now_str}")) % 1000000
        mission_id = f"msn-{hash_id:06d}"
        request_id = f"req-{hash_id:06d}"

        metadata = {
            "primary_command": primary_cmd,
            "instruction": instruction,
            "cwd": str(cwd),
            "project_type": ctx.project_type.value if hasattr(ctx.project_type, "value") else str(ctx.project_type),
        }

        return MissionRequest(
            mission_id=mission_id,
            request_id=request_id,
            original_command=raw_command,
            normalized_command=normalized,
            raw_prompt=raw_command,
            workspace=ctx.workspace_root,
            workspace_metadata=ws_meta_snapshot,
            timestamp=now_str,
            requested_at=now_str,
            mission_state=MissionState.RECEIVED,
            source="cli",
            version="1.0.0",
            parameters=parameters or {},
            metadata=metadata,
        )

    def parse_cli_command(
        self, raw_args: list[str], explicit_workspace: Any = None
    ) -> MissionRequest:
        """Parse raw CLI argument tokens into a MissionRequest."""
        raw_command = " ".join(raw_args)
        exp_path = Path(explicit_workspace) if explicit_workspace else None
        return self.process_intake(raw_command, explicit_workspace=exp_path)
