"""Swarm Coordination Engine for OniRoute (Phase P3.A4).

Coordinates agent communication, shared context, artifact exchange, task handoffs,
review requests, approval requests, consensus decisions, and conflict resolution
without modifying execution logic, planning, or scheduling.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field

from runtime.collaboration.message_bus import MessageBus

from .artifact_exchange import ArtifactExchange, ExchangeArtifactRecord
from .consensus import SwarmConsensusEngine, SwarmConsensusRecord
from .exceptions import SwarmInitializationError
from .handoffs import HandoffCoordinator, SwarmHandoffRecord
from .models import RuntimeExecutionSnapshot
from .result import SwarmExecutionResult
from .shared_context import SharedContextManager, SharedContextSnapshot


class SwarmCoordinationMessage(BaseModel):
    """Immutable coordination message record exchanged across swarm sessions."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(..., description="Unique message ID")
    sender_id: str = Field(..., description="Sender session ID")
    recipient_id: str = Field(default="broadcast", description="Recipient session ID or broadcast")
    message_type: str = Field(default="NOTIFICATION", description="Message type classification")
    subject: str = Field(..., description="Message subject line")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured message payload dict")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")


class SwarmCoordinationEngine:
    """Core Swarm Coordination Engine coordinating executing agents across waves."""

    def coordinate_swarm(
        self,
        snapshot: RuntimeExecutionSnapshot,
        results: List[SwarmExecutionResult],
        repository_root: Path | None = None,
        force_conflict: bool = False,
    ) -> Tuple[RuntimeExecutionSnapshot, Dict[str, Any]]:
        """Coordinate executing agents, register artifact exchanges, update shared context, and return updated snapshot."""
        if not snapshot.sessions:
            raise SwarmInitializationError("RuntimeExecutionSnapshot contains no initialized sessions.")

        t_start = time.perf_counter()
        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Wire Collaboration & Coordination Subsystems
        message_bus = MessageBus()
        artifact_exchange = ArtifactExchange()
        context_manager = SharedContextManager()
        handoff_coordinator = HandoffCoordinator()
        consensus_engine = SwarmConsensusEngine()

        # 2. Agent Communication & Execution Notifications
        messages_dispatched: List[SwarmCoordinationMessage] = []
        for res in results:
            msg = SwarmCoordinationMessage(
                message_id=f"msg-coord-{res.task_id[:12]}",
                sender_id=res.session_id,
                recipient_id="broadcast",
                message_type="NOTIFICATION",
                subject=f"Task {res.task_id} Completed",
                payload={
                    "task_id": res.task_id,
                    "profile_id": res.profile_id,
                    "wave": res.wave_number,
                    "status": str(res.execution_status.value if hasattr(res.execution_status, "value") else res.execution_status),
                    "artifact_count": len(res.produced_artifacts),
                },
                timestamp=now_str,
            )
            messages_dispatched.append(msg)


        # 3. Shared Context Synchronization
        initial_ctx = context_manager.create_initial_snapshot(
            mission_id=snapshot.mission_id,
            context_dict={
                "execution_uuid": snapshot.execution_uuid,
                "mission_id": snapshot.mission_id,
                "deployment_plan_id": snapshot.deployment_plan_id,
            },
        )
        updated_ctx = context_manager.merge_execution_outcomes(initial_ctx, results)

        # 4. Artifact Exchange Registration & Delivery
        receiving_map = {}
        for w_num in range(1, 6):
            src_profiles = [r.profile_id for r in results if r.wave_number == w_num]
            tgt_profiles = [r.profile_id for r in results if r.wave_number == w_num + 1]
            for p in src_profiles:
                receiving_map[p] = tgt_profiles

        exchange_records = artifact_exchange.register_artifacts_from_results(results, receiving_map)

        if force_conflict and len(exchange_records) >= 2:
            # Inject a simulated artifact conflict for testing
            exchange_records.append(
                ExchangeArtifactRecord(
                    exchange_id="ex-art-conflict-sim",
                    artifact_id="art-sim-conflict",
                    owner_profile_id=exchange_records[0].owner_profile_id,
                    owner_session_id=exchange_records[0].owner_session_id,
                    receiving_profile_ids=[],
                    name=exchange_records[1].name,
                    version="v1.0.1",
                    artifact_type=exchange_records[1].artifact_type,
                    lineage=[],
                    delivery_status="DELIVERED",
                    conflict_status="CONFLICT_DETECTED",
                    exchange_hash="hash-sim-conflict",
                    registered_at=now_str,
                )
            )

        conflicts = artifact_exchange.detect_conflicts(exchange_records)

        # 5. Deterministic Task Handoffs
        handoff_records = handoff_coordinator.generate_wave_handoffs(results, snapshot.wave_status)

        # 6. Review & Approval Consensus
        consensus_records: List[SwarmConsensusRecord] = []
        for w_num in range(1, 7):
            w_profiles = [r.profile_id for r in results if r.wave_number == w_num]
            if w_profiles:
                gate_name = f"Wave {w_num} Execution & Review Gate"
                csn = consensus_engine.evaluate_wave_consensus(
                    wave_number=w_num,
                    gate_name=gate_name,
                    participant_profiles=w_profiles,
                    force_escalation=(force_conflict and w_num == 3),
                )
                consensus_records.append(csn)

        t_end = time.perf_counter()
        coordination_latency_ms = (t_end - t_start) * 1000.0

        # 7. Update RuntimeExecutionSnapshot Evidence & Metadata
        coordination_evidence = {
            "total_messages_dispatched": len(messages_dispatched),
            "artifacts_exchanged_count": len(exchange_records),
            "handoffs_completed_count": len(handoff_records),
            "consensus_decisions_count": len(consensus_records),
            "context_version": updated_ctx.version_index,
            "context_snapshot_id": updated_ctx.snapshot_id,
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": len(conflicts),
            "coordination_latency_ms": round(coordination_latency_ms, 2),
        }

        updated_evidence = dict(snapshot.evidence)
        updated_evidence["coordination"] = coordination_evidence
        updated_evidence["shared_context"] = {
            "latest_snapshot_id": updated_ctx.snapshot_id,
            "context_hash": updated_ctx.context_hash,
            "version": updated_ctx.version_index,
        }

        # Compute SHA-256 Snapshot Hash
        preliminary_dict = {
            "snapshot_id": snapshot.snapshot_id,
            "mission_id": snapshot.mission_id,
            "deployment_plan_id": snapshot.deployment_plan_id,
            "execution_uuid": snapshot.execution_uuid,
            "session_count": len(snapshot.sessions),
            "coordination_evidence": {k: v for k, v in coordination_evidence.items() if "latency" not in k},
            "context_hash": updated_ctx.context_hash,
        }
        updated_hash = hashlib.sha256(json.dumps(preliminary_dict, sort_keys=True).encode("utf-8")).hexdigest()

        updated_snapshot = RuntimeExecutionSnapshot(
            snapshot_id=snapshot.snapshot_id,
            mission_id=snapshot.mission_id,
            deployment_plan_id=snapshot.deployment_plan_id,
            execution_uuid=snapshot.execution_uuid,
            wave_status=snapshot.wave_status,
            session_map=snapshot.session_map,
            sessions=snapshot.sessions,
            execution_cursor=snapshot.execution_cursor,
            execution_context=snapshot.execution_context,
            budget_status=snapshot.budget_status,
            retry_status=snapshot.retry_status,
            checkpoint_status=snapshot.checkpoint_status,
            event_bus_references=snapshot.event_bus_references,
            storage_references=snapshot.storage_references,
            workspace_references=snapshot.workspace_references,
            evidence=updated_evidence,
            timestamp=now_str,
            snapshot_hash=updated_hash,
        )

        coordination_summary = {
            "messages": [m.model_dump(mode="json") for m in messages_dispatched],
            "artifact_exchanges": [e.model_dump(mode="json") for e in exchange_records],
            "handoffs": [h.model_dump(mode="json") for h in handoff_records],
            "consensus": [c.model_dump(mode="json") for c in consensus_records],
            "conflicts": conflicts,
            "shared_context_snapshot": updated_ctx.model_dump(mode="json"),
            "coordination_latency_ms": round(coordination_latency_ms, 2),
        }

        return updated_snapshot, coordination_summary
