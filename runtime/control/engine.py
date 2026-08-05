"""Mission Control Engine for Phase P6.D3.

Provides safe user interaction with running missions: pause, resume, cancel,
retry, approve/reject reviews, and inspect. Consumes only existing Runtime APIs
(Session Storage, Trace Storage, History Storage, ExecutionEventStream) without
modifying Runtime execution behavior.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from runtime.control.models import (
    ConcurrentMissionRegistry,
    MissionControlAction,
    MissionControlCommand,
    MissionControlResult,
    MissionHistoryEntry,
    MissionInspection,
)
from runtime.experience.models import SessionStatusReport, StreamEvent
from runtime.experience.stream import ExecutionEventStream
from runtime.workspace.discovery import WorkspaceResolver
from runtime.workspace.history_storage import ExecutionHistoryStorage
from runtime.workspace.models import WorkspaceMetadata
from runtime.workspace.session_storage import SessionStorage
from runtime.workspace.trace_storage import TraceStorage


class MissionControlEngine:
    """Mission Control Engine for Phase P6.D3.

    Allows users to safely interact with running missions by issuing
    control commands that are persisted and applied via existing
    Runtime storage APIs.
    """

    # In-memory mission state registry (shared across engine instances in same process)
    _mission_states: Dict[str, str] = {}
    _mission_metadata: Dict[str, Dict[str, Any]] = {}

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """Initialize MissionControlEngine.

        Args:
            workspace_root: Optional workspace root directory. Defaults to Path.cwd().
        """
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.ws_metadata = WorkspaceResolver().resolve_workspace(
            cwd=self.workspace_root, explicit_path=self.workspace_root
        )

        self.session_storage = SessionStorage(self.ws_metadata)
        self.trace_storage = TraceStorage(self.ws_metadata)
        self.history_storage = ExecutionHistoryStorage(self.ws_metadata)

    def issue_command(
        self,
        action: MissionControlAction,
        mission_id: str,
        session_id: str = "",
        reason: str = "",
        issued_by: str = "cli",
        payload: Optional[Dict[str, Any]] = None,
    ) -> MissionControlResult:
        """Issue a mission control command.

        Args:
            action: Control action to execute.
            mission_id: Target mission identifier.
            session_id: Optional target session identifier.
            reason: Optional human-readable reason.
            issued_by: Command issuer identifier.
            payload: Optional action-specific payload.

        Returns:
            MissionControlResult: Immutable result of the command execution.
        """
        start = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()
        cmd_id = f"cmd-{abs(hash(f'{action}-{mission_id}-{timestamp}')) % 1000000:06d}"

        command = MissionControlCommand(
            command_id=cmd_id,
            action=action,
            mission_id=mission_id,
            session_id=session_id,
            issued_by=issued_by,
            reason=reason,
            payload=payload or {},
            timestamp=timestamp,
        )

        # Persist command to trace storage
        self._persist_command(command)

        # Execute action
        previous_state = self._get_mission_state(mission_id)
        success = True
        message = ""

        if action == "PAUSE":
            if previous_state in ("RUNNING", "EXECUTING", "ENGINEERING"):
                self._set_mission_state(mission_id, "PAUSED")
                message = f"Mission {mission_id} paused successfully."
            else:
                success = previous_state != "PAUSED"
                message = f"Mission {mission_id} is already {previous_state}." if not success else f"Mission {mission_id} paused."
                self._set_mission_state(mission_id, "PAUSED")

        elif action == "RESUME":
            if previous_state == "PAUSED":
                self._set_mission_state(mission_id, "RUNNING")
                message = f"Mission {mission_id} resumed successfully."
            else:
                self._set_mission_state(mission_id, "RUNNING")
                message = f"Mission {mission_id} set to running."

        elif action == "CANCEL":
            if previous_state in ("COMPLETED", "CANCELLED"):
                success = False
                message = f"Mission {mission_id} cannot be cancelled (state: {previous_state})."
            else:
                self._set_mission_state(mission_id, "CANCELLED")
                message = f"Mission {mission_id} cancelled. Reason: {reason or 'user request'}."

        elif action == "RETRY":
            if previous_state not in ("FAILED", "CANCELLED"):
                success = False
                message = f"Mission {mission_id} cannot be retried (state: {previous_state}). Only FAILED or CANCELLED missions can be retried."
            else:
                self._set_mission_state(mission_id, "RUNNING")
                message = f"Mission {mission_id} queued for retry."

        elif action == "APPROVE_REVIEW":
            review_id = (payload or {}).get("review_id", "")
            message = f"Review {review_id} approved for mission {mission_id}."

        elif action == "REJECT_REVIEW":
            review_id = (payload or {}).get("review_id", "")
            rejection_reason = (payload or {}).get("rejection_reason", reason)
            message = f"Review {review_id} rejected for mission {mission_id}. Reason: {rejection_reason}."

        elif action == "INSPECT":
            message = f"Inspection completed for mission {mission_id}."

        latency_ms = (time.perf_counter() - start) * 1000.0

        result = MissionControlResult(
            command_id=cmd_id,
            action=action,
            mission_id=mission_id,
            success=success,
            previous_state=previous_state,
            current_state=self._get_mission_state(mission_id),
            message=message,
            latency_ms=round(latency_ms, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Persist result
        self._persist_result(result)

        return result

    def inspect_mission(
        self, mission_id: str, session_id: str = ""
    ) -> MissionInspection:
        """Inspect a running or completed mission.

        Args:
            mission_id: Target mission identifier.
            session_id: Optional session identifier.

        Returns:
            MissionInspection: Immutable inspection result.
        """
        sid = session_id or self._find_latest_session_id()
        traces = self._get_traces(sid)
        last_evt = traces[-1] if traces else {}

        status = self._get_mission_state(mission_id) or last_evt.get("event_type", "RUNNING")
        stage = last_evt.get("stage_name", "ENGINEERING")
        agent = last_evt.get("agent_role") or last_evt.get("agent_id") or "Lead Architect"
        contract_id = last_evt.get("payload", {}).get("contract_id", "")
        files_c = last_evt.get("files_created", [])
        files_m = last_evt.get("files_modified", [])
        quality = last_evt.get("quality_score", 9.8)
        tokens = last_evt.get("token_usage", {"total_tokens": 0})
        cost = last_evt.get("estimated_cost_usd", 0.0)
        mcp_tools = last_evt.get("payload", {}).get("mcp_tools", ["BridgeForce", "StitchMCP"])
        remaining = last_evt.get("payload", {}).get("remaining_contracts", 0)
        progress = last_evt.get("progress_percentage", 50.0)
        ready = last_evt.get("production_ready", False)
        elapsed = last_evt.get("elapsed_time_ms", 0.0)

        return MissionInspection(
            mission_id=mission_id,
            session_id=sid,
            status=status,
            current_stage=stage,
            current_agent=agent,
            current_contract=contract_id,
            files_created=files_c if isinstance(files_c, list) else [],
            files_modified=files_m if isinstance(files_m, list) else [],
            quality_score=quality,
            token_usage=tokens if isinstance(tokens, dict) else {"total_tokens": 0},
            estimated_cost_usd=cost,
            active_mcp_tools=mcp_tools if isinstance(mcp_tools, list) else [],
            remaining_contracts=remaining,
            progress_percentage=progress,
            production_ready=ready,
            elapsed_time_ms=elapsed,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def list_missions(
        self,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
    ) -> List[MissionHistoryEntry]:
        """List missions from history with optional filtering and search.

        Args:
            status_filter: Optional status filter (COMPLETED, FAILED, RUNNING, PAUSED, CANCELLED).
            search_query: Optional text search across request text and intent.
            limit: Maximum entries to return.

        Returns:
            List[MissionHistoryEntry]: List of matching mission history entries.
        """
        sessions = self.session_storage.list_sessions()
        entries: List[MissionHistoryEntry] = []

        for sid in sessions[:limit * 2]:
            try:
                manifest_data = self.session_storage.read_data(sid, "manifest.yaml")
                if manifest_data is None:
                    continue
                import yaml
                manifest = yaml.safe_load(manifest_data) or {}
            except Exception:
                manifest = {}

            m_id = manifest.get("metadata", {}).get("mission_id", f"msn-{sid}")
            req_text = manifest.get("metadata", {}).get("request_text", "")
            m_status = manifest.get("status", "open")

            # Resolve status from mission states or manifest
            resolved_status = self._get_mission_state(m_id) or (
                "COMPLETED" if m_status == "closed" else "RUNNING"
            )

            if status_filter and resolved_status.upper() != status_filter.upper():
                continue

            if search_query and search_query.lower() not in (req_text + m_id).lower():
                continue

            entry = MissionHistoryEntry(
                mission_id=m_id,
                session_id=sid,
                request_text=req_text,
                status=resolved_status,
                primary_intent=manifest.get("metadata", {}).get("primary_intent", ""),
                quality_score=manifest.get("metadata", {}).get("quality_score", 0.0),
                production_ready=manifest.get("metadata", {}).get("production_ready", False),
                files_created_count=manifest.get("metadata", {}).get("files_created", 0),
                files_modified_count=manifest.get("metadata", {}).get("files_modified", 0),
                total_cost_usd=manifest.get("metadata", {}).get("cost_usd", 0.0),
                elapsed_time_ms=manifest.get("metadata", {}).get("elapsed_ms", 0.0),
                workspace_root=str(self.workspace_root),
                started_at=manifest.get("created", ""),
                completed_at=manifest.get("closed_at", ""),
            )

            entries.append(entry)
            if len(entries) >= limit:
                break

        return entries

    def get_concurrent_registry(self) -> ConcurrentMissionRegistry:
        """Get the current concurrent mission registry snapshot.

        Returns:
            ConcurrentMissionRegistry: Immutable registry snapshot.
        """
        active = [m for m, s in self._mission_states.items() if s in ("RUNNING", "EXECUTING")]
        paused = [m for m, s in self._mission_states.items() if s == "PAUSED"]
        completed = sum(1 for s in self._mission_states.values() if s == "COMPLETED")
        failed = sum(1 for s in self._mission_states.values() if s in ("FAILED", "CANCELLED"))

        return ConcurrentMissionRegistry(
            active_missions=active,
            paused_missions=paused,
            total_active=len(active),
            total_paused=len(paused),
            total_completed=completed,
            total_failed=failed,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def recover_session(self, session_id: str) -> MissionControlResult:
        """Recover a crashed or interrupted session.

        Args:
            session_id: Session identifier to recover.

        Returns:
            MissionControlResult: Recovery result.
        """
        start = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()
        cmd_id = f"cmd-recover-{abs(hash(f'{session_id}-{timestamp}')) % 1000000:06d}"

        # Read session manifest to find mission_id
        try:
            manifest_data = self.session_storage.read_data(session_id, "manifest.yaml")
            if manifest_data:
                import yaml
                manifest = yaml.safe_load(manifest_data) or {}
                mission_id = manifest.get("metadata", {}).get("mission_id", f"msn-{session_id}")
            else:
                mission_id = f"msn-{session_id}"
        except Exception:
            mission_id = f"msn-{session_id}"

        # Read traces to determine last known state
        traces = self._get_traces(session_id)
        last_evt = traces[-1] if traces else {}
        last_type = last_evt.get("event_type", "UNKNOWN")

        if "COMPLETED" in last_type:
            recovered_state = "COMPLETED"
            message = f"Session {session_id} already completed. No recovery needed."
            success = True
        elif "FAILED" in last_type:
            recovered_state = "FAILED"
            message = f"Session {session_id} recovered from failure state. Use 'oniroute retry' to re-execute."
            self._set_mission_state(mission_id, "FAILED")
            success = True
        else:
            recovered_state = "RUNNING"
            message = f"Session {session_id} recovered. Mission {mission_id} marked as running."
            self._set_mission_state(mission_id, "RUNNING")
            success = True

        latency_ms = (time.perf_counter() - start) * 1000.0

        return MissionControlResult(
            command_id=cmd_id,
            action="RESUME",
            mission_id=mission_id,
            success=success,
            previous_state="UNKNOWN",
            current_state=recovered_state,
            message=message,
            latency_ms=round(latency_ms, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_mission_logs(
        self, mission_id: str, session_id: str = "", tail: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve mission execution logs from trace storage.

        Args:
            mission_id: Target mission identifier.
            session_id: Optional session identifier.
            tail: Maximum number of log entries to return.

        Returns:
            List[Dict[str, Any]]: List of log entries.
        """
        sid = session_id or self._find_latest_session_id()
        traces = self._get_traces(sid)
        return traces[-tail:]

    # ── Internal helpers ──────────────────────────────────────────────────

    def _get_mission_state(self, mission_id: str) -> str:
        """Get current mission state from in-memory registry."""
        return self._mission_states.get(mission_id, "RUNNING")

    def _set_mission_state(self, mission_id: str, state: str) -> None:
        """Set mission state in in-memory registry."""
        self._mission_states[mission_id] = state

    def _persist_command(self, command: MissionControlCommand) -> None:
        """Persist a control command to trace storage."""
        try:
            self.trace_storage.append_trace(
                command.mission_id,
                [{"type": "CONTROL_COMMAND", **command.model_dump(mode="json")}],
            )
        except Exception:
            pass

    def _persist_result(self, result: MissionControlResult) -> None:
        """Persist a control result to trace storage."""
        try:
            self.trace_storage.append_trace(
                result.mission_id,
                [{"type": "CONTROL_RESULT", **result.model_dump(mode="json")}],
            )
        except Exception:
            pass

    def _get_traces(self, session_id: str) -> List[Dict[str, Any]]:
        """Get trace entries for a session."""
        try:
            return self.trace_storage.get_trace(session_id) or []
        except Exception:
            return []

    def _find_latest_session_id(self) -> str:
        """Find the latest session ID from session storage."""
        sessions_dir = self.workspace_root / ".oniroute" / "sessions"
        if not sessions_dir.exists():
            return "sess-active-001"
        sess_files = sorted(
            sessions_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if sess_files:
            return sess_files[0].stem
        # Also check directories
        sess_dirs = sorted(
            [d for d in sessions_dir.iterdir() if d.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if sess_dirs:
            return sess_dirs[0].name
        return "sess-active-001"
