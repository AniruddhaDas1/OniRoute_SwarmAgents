"""Deterministic Artifact Exchange for Swarm Coordination (Phase P3.A4).

Registers, versions, delivers, and tracks lineage for produced artifacts
without regenerating any artifacts.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from runtime.agent.models import ArtifactRecord


class ExchangeArtifactRecord(BaseModel):
    """Immutable exchange record for a registered artifact."""

    model_config = ConfigDict(frozen=True)

    exchange_id: str = Field(..., description="Unique exchange ID (ex-art-xxxxxx)")
    artifact_id: str = Field(..., description="Target artifact ID")
    owner_profile_id: str = Field(..., description="Owner AgentProfile ID")
    owner_session_id: str = Field(..., description="Owner AgentSession ID")
    receiving_profile_ids: List[str] = Field(default_factory=list, description="Target receiving AgentProfile IDs")
    name: str = Field(..., description="Artifact name")
    version: str = Field(default="v1.0.0", description="Artifact semver string")
    artifact_type: str = Field(..., description="Artifact category type")
    lineage: List[str] = Field(default_factory=list, description="Parent artifact IDs")
    delivery_status: str = Field(default="DELIVERED", description="Delivery status (DELIVERED, CONFIRMED)")
    conflict_status: str = Field(default="NO_CONFLICT", description="Conflict status (NO_CONFLICT, CONFLICT_DETECTED, RESOLVED)")
    exchange_hash: str = Field(..., description="SHA-256 exchange hash")
    registered_at: str = Field(..., description="ISO-8601 UTC timestamp")


class ArtifactExchange:
    """Deterministic Artifact Exchange manager."""

    def __init__(self) -> None:
        self._records: Dict[str, ExchangeArtifactRecord] = {}
        self._artifact_history: Dict[str, List[ExchangeArtifactRecord]] = {}

    def register_artifacts_from_results(
        self,
        results: List[Any],
        receiving_map: Optional[Dict[str, List[str]]] = None,
    ) -> List[ExchangeArtifactRecord]:
        """Register all produced artifacts from SwarmExecutionResult records."""
        now_str = datetime.now(timezone.utc).isoformat()
        registered: List[ExchangeArtifactRecord] = []

        for res in results:
            for art in res.produced_artifacts:
                art_id = art.artifact_id if hasattr(art, "artifact_id") else art.get("artifact_id", "art-unknown")
                art_name = art.name if hasattr(art, "name") else art.get("name", "Unnamed Deliverable")
                art_type = art.artifact_type if hasattr(art, "artifact_type") else art.get("artifact_type", "code")
                lineage = art.lineage if hasattr(art, "lineage") else art.get("lineage", [])

                receivers = receiving_map.get(res.profile_id, []) if receiving_map else []
                ex_id = f"ex-{art_id[:12]}"

                payload = {
                    "exchange_id": ex_id,
                    "artifact_id": art_id,
                    "owner_profile_id": res.profile_id,
                    "session_id": res.session_id,
                    "receivers": receivers,
                }
                ex_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

                record = ExchangeArtifactRecord(
                    exchange_id=ex_id,
                    artifact_id=art_id,
                    owner_profile_id=res.profile_id,
                    owner_session_id=res.session_id,
                    receiving_profile_ids=receivers,
                    name=art_name,
                    version="v1.0.0",
                    artifact_type=str(art_type.value if hasattr(art_type, "value") else art_type),
                    lineage=list(lineage),
                    delivery_status="DELIVERED" if receivers else "CONFIRMED",
                    conflict_status="NO_CONFLICT",
                    exchange_hash=ex_hash,
                    registered_at=now_str,
                )

                self._records[ex_id] = record
                if art_id not in self._artifact_history:
                    self._artifact_history[art_id] = []
                self._artifact_history[art_id].append(record)
                registered.append(record)

        return registered

    def confirm_delivery(self, exchange_id: str) -> Optional[ExchangeArtifactRecord]:
        """Confirm delivery of a registered artifact exchange record."""
        rec = self._records.get(exchange_id)
        if not rec:
            return None

        updated = ExchangeArtifactRecord(
            exchange_id=rec.exchange_id,
            artifact_id=rec.artifact_id,
            owner_profile_id=rec.owner_profile_id,
            owner_session_id=rec.owner_session_id,
            receiving_profile_ids=rec.receiving_profile_ids,
            name=rec.name,
            version=rec.version,
            artifact_type=rec.artifact_type,
            lineage=rec.lineage,
            delivery_status="CONFIRMED",
            conflict_status=rec.conflict_status,
            exchange_hash=rec.exchange_hash,
            registered_at=rec.registered_at,
        )
        self._records[exchange_id] = updated
        return updated

    def detect_conflicts(self, records: List[ExchangeArtifactRecord]) -> List[Dict[str, Any]]:
        """Detect naming or concurrent modification conflicts among registered artifacts."""
        seen_names: Dict[str, str] = {}
        conflicts: List[Dict[str, Any]] = []

        for rec in records:
            if rec.name in seen_names and seen_names[rec.name] != rec.owner_profile_id:
                conflicts.append(
                    {
                        "conflict_id": f"cfl-art-{rec.exchange_id[:8]}",
                        "artifact_name": rec.name,
                        "owner_profile_a": seen_names[rec.name],
                        "owner_profile_b": rec.owner_profile_id,
                        "resolution_strategy": "VERSION_BRANCH",
                        "resolved": True,
                    }
                )
            else:
                seen_names[rec.name] = rec.owner_profile_id

        return conflicts

    def get_all_records(self) -> List[ExchangeArtifactRecord]:
        """Return all registered exchange records."""
        return list(self._records.values())
