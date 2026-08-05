"""Deterministic Task Handoffs for Swarm Coordination (Phase P3.A4).

Flow: Completed Task -> Artifact Exchange -> Receiving Profile -> Acknowledgement -> Execution Continues
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SwarmHandoffRecord(BaseModel):
    """Immutable handoff record transferring task artifacts to receiving profiles."""

    model_config = ConfigDict(frozen=True)

    handoff_id: str = Field(..., description="Unique handoff record ID (hdf-wX-xxxxxx)")
    source_profile_id: str = Field(..., description="Source AgentProfile ID completing the task")
    receiving_profile_id: str = Field(..., description="Target receiving AgentProfile ID")
    source_wave: int = Field(..., ge=1, le=6, description="Source task wave number")
    target_wave: int = Field(..., ge=1, le=6, description="Target task wave number")
    transferred_artifact_ids: List[str] = Field(default_factory=list, description="List of transferred artifact IDs")
    status: str = Field(default="ACKNOWLEDGED", description="Handoff status (INITIATED, ACKNOWLEDGED, COMPLETED)")
    handoff_hash: str = Field(..., description="SHA-256 handoff hash")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")


class HandoffCoordinator:
    """Coordinator for deterministic task handoffs across execution waves."""

    def __init__(self) -> None:
        self._records: Dict[str, SwarmHandoffRecord] = {}

    def generate_wave_handoffs(
        self,
        results: List[Any],
        wave_status: Dict[int, Any],
    ) -> List[SwarmHandoffRecord]:
        """Generate deterministic handoff records between consecutive execution waves."""
        now_str = datetime.now(timezone.utc).isoformat()
        records: List[SwarmHandoffRecord] = []

        # Map results by wave
        wave_results: Dict[int, List[Any]] = {}
        for res in results:
            w = res.wave_number
            if w not in wave_results:
                wave_results[w] = []
            wave_results[w].append(res)

        for w_num in range(1, 6):
            current_wave_res = wave_results.get(w_num, [])
            next_wave_res = wave_results.get(w_num + 1, [])

            if not current_wave_res or not next_wave_res:
                continue

            for src in current_wave_res:
                art_ids = [a.artifact_id if hasattr(a, "artifact_id") else a.get("artifact_id") for a in src.produced_artifacts]
                for tgt in next_wave_res:
                    hdf_id = f"hdf-w{w_num}to{w_num+1}-{src.profile_id[:6]}-{tgt.profile_id[:6]}"

                    payload = {
                        "handoff_id": hdf_id,
                        "source": src.profile_id,
                        "target": tgt.profile_id,
                        "artifacts": art_ids,
                    }
                    hdf_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

                    record = SwarmHandoffRecord(
                        handoff_id=hdf_id,
                        source_profile_id=src.profile_id,
                        receiving_profile_id=tgt.profile_id,
                        source_wave=w_num,
                        target_wave=w_num + 1,
                        transferred_artifact_ids=art_ids,
                        status="ACKNOWLEDGED",
                        handoff_hash=hdf_hash,
                        timestamp=now_str,
                    )

                    self._records[hdf_id] = record
                    records.append(record)

        return records

    def get_all_handoffs(self) -> List[SwarmHandoffRecord]:
        """Return all recorded handoff records."""
        return list(self._records.values())
