"""Immutable Shared Context Management for Swarm Coordination (Phase P3.A4).

Maintains versioned shared context snapshots, supports reading, merging,
and conflict detection without mutating past context records.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SharedContextSnapshot(BaseModel):
    """Immutable snapshot representation of the shared swarm context state."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(..., description="Unique shared context snapshot ID (ctx-snap-xxxxxx)")
    version_index: int = Field(default=1, ge=1, description="Sequential version index integer")
    previous_snapshot_id: Optional[str] = Field(default=None, description="Parent snapshot ID for lineage tracking")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Key-value shared context state data")
    conflict_log: List[Dict[str, Any]] = Field(default_factory=list, description="Conflict detection log records")
    context_hash: str = Field(..., description="SHA-256 context hash")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")


class SharedContextManager:
    """Manager for maintaining immutable versioned shared context snapshots."""

    def __init__(self) -> None:
        self._history: List[SharedContextSnapshot] = []

    def create_initial_snapshot(self, mission_id: str, context_dict: Dict[str, Any]) -> SharedContextSnapshot:
        """Create the genesis shared context snapshot."""
        now_str = datetime.now(timezone.utc).isoformat()
        snap_id = f"ctx-snap-w1-init-{hashlib.sha256(mission_id.encode()).hexdigest()[:8]}"

        payload = {"snapshot_id": snap_id, "version_index": 1, "data": context_dict}
        ctx_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        snapshot = SharedContextSnapshot(
            snapshot_id=snap_id,
            version_index=1,
            previous_snapshot_id=None,
            context_data=dict(context_dict),
            conflict_log=[],
            context_hash=ctx_hash,
            timestamp=now_str,
        )
        self._history.append(snapshot)
        return snapshot

    def merge_execution_outcomes(
        self,
        current_snapshot: SharedContextSnapshot,
        results: List[Any],
    ) -> SharedContextSnapshot:
        """Merge execution task outcomes into a new versioned SharedContextSnapshot."""
        now_str = datetime.now(timezone.utc).isoformat()
        next_version = current_snapshot.version_index + 1
        ver_slug = f"v{next_version}-{current_snapshot.snapshot_id}"
        snap_id = f"ctx-snap-v{next_version}-{hashlib.sha256(ver_slug.encode()).hexdigest()[:8]}"


        updated_data = dict(current_snapshot.context_data)
        conflicts: List[Dict[str, Any]] = []

        for res in results:
            key = f"task_outcome_{res.task_id}"
            new_val = {
                "profile_id": res.profile_id,
                "session_id": res.session_id,
                "wave": res.wave_number,
                "status": str(res.execution_status.value if hasattr(res.execution_status, "value") else res.execution_status),
                "tokens": res.consumed_tokens,
                "cost": res.cost_usd,
                "artifacts_count": len(res.produced_artifacts),
            }

            if key in updated_data and updated_data[key] != new_val:
                conflicts.append(
                    {
                        "conflict_id": f"cfl-ctx-{res.task_id[:8]}",
                        "key": key,
                        "old_value": updated_data[key],
                        "new_value": new_val,
                        "resolved": True,
                    }
                )
            updated_data[key] = new_val

        updated_data["total_tasks_completed"] = len(results)
        updated_data["last_updated_wave"] = max((r.wave_number for r in results), default=1)

        payload = {"snapshot_id": snap_id, "version_index": next_version, "data": updated_data}
        ctx_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        snapshot = SharedContextSnapshot(
            snapshot_id=snap_id,
            version_index=next_version,
            previous_snapshot_id=current_snapshot.snapshot_id,
            context_data=updated_data,
            conflict_log=conflicts,
            context_hash=ctx_hash,
            timestamp=now_str,
        )
        self._history.append(snapshot)
        return snapshot

    def get_latest_snapshot(self) -> Optional[SharedContextSnapshot]:
        """Return the most recent shared context snapshot."""
        return self._history[-1] if self._history else None
