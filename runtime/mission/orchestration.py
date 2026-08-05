"""Mission Orchestration component for OniRoute Mission Orchestrator (ACR-004 Phase O4).

Mission Orchestration converts a VALIDATED Mission into a canonical ExecutionRequest.

It orchestrates existing frozen engines by preparing:
- Planning Preparation (PlanningRequest payload without plan generation)
- Governance Preparation (GovernanceRequest payload without policy evaluation)
- Workspace Preparation (Workspace Runtime subdirectories without filesystem writes)
- UMAL Preparation (ModelRequest payload without model selection)
- Invocation Preparation (InvocationRequest payload without execution)

It MUST NOT implement planning.
It MUST NOT execute workflows.
It MUST NOT select agents or skills.
It MUST NOT select models.
It MUST NOT invoke AI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import MissionOrchestratorContract
from .exceptions import InvalidMissionStateError, MissionOrchestrationError
from .models import (
    ExecutionRequest,
    Mission,
    MissionConstraints,
    MissionContext,
    MissionState,
    MissionStatus,
)
from .states import can_transition


class MissionOrchestrator(MissionOrchestratorContract):
    """Concrete Mission Orchestrator component producing canonical ExecutionRequests."""

    def orchestrate_mission(self, mission: Mission) -> ExecutionRequest:
        """Convert a VALIDATED Mission into a canonical ExecutionRequest."""
        # 1. State machine validation
        if mission.status.current_state not in (MissionState.VALIDATED, MissionState.ORCHESTRATED):
            raise InvalidMissionStateError(
                f"Cannot orchestrate mission '{mission.mission_id}' from '{mission.status.current_state}' state. "
                "Mission must be in VALIDATED state."
            )

        # 2. Transition state to ORCHESTRATED if needed
        now_str = datetime.now(timezone.utc).isoformat()
        current_state = mission.status.current_state

        history = list(mission.status.state_history)
        if current_state == MissionState.VALIDATED:
            if not can_transition(MissionState.VALIDATED, MissionState.ORCHESTRATED):
                raise InvalidMissionStateError("Cannot transition from VALIDATED to ORCHESTRATED.")
            history.append(
                {
                    "from_state": MissionState.VALIDATED.value,
                    "to_state": MissionState.ORCHESTRATED.value,
                    "reason": "Mission Orchestration prepared",
                    "timestamp": now_str,
                }
            )

        orchestrated_status = MissionStatus(
            current_state=MissionState.ORCHESTRATED,
            state_history=history,
            current_step="Mission Orchestration Prepared",
            progress_percentage=100.0,
            started_at=mission.status.started_at,
            updated_at=now_str,
        )

        # 3. Preparation steps (delegating to framework components without execution)
        planning_req, planning_ev = self._prepare_planning(mission)
        governance_req, governance_ev = self._prepare_governance(mission)
        workspace_req, workspace_ev = self._prepare_workspace(mission)
        umal_req, umal_ev = self._prepare_umal(mission)
        invocation_req, invocation_ev = self._prepare_invocation(mission)

        # 4. Immutable evidence aggregation
        evidence = mission.evidence
        evidence = evidence.record_stage("planning_prep", planning_ev)
        evidence = evidence.record_stage("governance_prep", governance_ev)
        evidence = evidence.record_stage("workspace_prep", workspace_ev)
        evidence = evidence.record_stage("umal_prep", umal_ev)
        evidence = evidence.record_stage("invocation_prep", invocation_ev)

        orchestration_ev = {
            "orchestrated": True,
            "prepared_at": now_str,
            "planning_prepared": True,
            "governance_prepared": True,
            "workspace_prepared": True,
            "umal_prepared": True,
            "invocation_prepared": True,
            "no_execution": True,
            "no_planning_generated": True,
            "no_policy_evaluated": True,
            "no_filesystem_writes": True,
            "no_model_selected": True,
            "no_ai_invocation": True,
        }
        evidence = evidence.record_stage("orchestration", orchestration_ev)

        # 5. Assemble updated Mission in ORCHESTRATED state
        mission_dict = mission.model_dump(mode="python")
        mission_dict["status"] = orchestrated_status
        mission_dict["evidence"] = evidence
        orchestrated_mission = Mission(**mission_dict)

        # 6. Construct ExecutionRequest
        exreq_id = f"exreq-{abs(hash(f'{mission.mission_id}:{now_str}')) % 1000000:06d}"

        exec_meta = {
            "execution_request_id": exreq_id,
            "mission_id": mission.mission_id,
            "prepared_at": now_str,
            "target_state": MissionState.ORCHESTRATED.value,
            "read_only_engine_confirmed": mission.context.read_only_engine_confirmed,
        }

        ws_meta = mission.request.workspace_metadata or {
            "workspace_root": str(mission.context.workspace_root),
            "engine_root": str(mission.context.engine_root),
            "project_type": mission.context.project_type,
        }

        return ExecutionRequest(
            request_id=exreq_id,
            mission=orchestrated_mission,
            mission_context=mission.context,
            mission_constraints=mission.constraints,
            workspace_metadata=ws_meta,
            planning_request=planning_req,
            governance_request=governance_req,
            umal_request=umal_req,
            invocation_request=invocation_req,
            execution_metadata=exec_meta,
            execution_evidence=evidence,
            execution_state=MissionState.ORCHESTRATED,
        )

    def _prepare_planning(self, mission: Mission) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare PlanningRequest payload without generating plans."""
        params = mission.request.parameters or {}
        req = {
            "mission_id": mission.mission_id,
            "primary_goal": mission.requirements.primary_goal,
            "intent_category": mission.requirements.intent_category,
            "constraints": mission.constraints.model_dump(mode="python"),
            "context": mission.context.model_dump(mode="python"),
            "workspace_root": str(mission.context.workspace_root),
            "dependencies": mission.evidence.repository.get("symbols_count", 0),
            "priority": params.get("priority", "normal"),
            "risk_level": params.get("risk_level", "low"),
            "status": "PREPARED",
            "no_plan_generated": True,
        }
        evidence = {
            "planning_prepared": True,
            "primary_goal": mission.requirements.primary_goal,
            "priority": req["priority"],
            "risk_level": req["risk_level"],
            "no_execution_plan": True,
        }
        return req, evidence

    def _prepare_governance(self, mission: Mission) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare GovernanceRequest payload without evaluating policies."""
        req = {
            "mission_id": mission.mission_id,
            "permissions": ["workspace:read", "workspace:write", "storage:persist"],
            "policies": ["engine_read_only", "budget_policy", "security_policy"],
            "budgets": {
                "max_budget_usd": mission.constraints.max_budget_usd,
                "timeout_seconds": mission.constraints.timeout_seconds,
            },
            "approvals": "REQUIRE_APPROVAL" if mission.constraints.require_human_approval else "AUTOMATIC",
            "security_context": {
                "read_only_engine_confirmed": mission.context.read_only_engine_confirmed,
                "allowed_providers": mission.constraints.allowed_providers,
                "local_only": mission.constraints.local_only,
            },
            "risk_metadata": {"risk_threshold": 100, "evaluated": False},
            "status": "PREPARED",
            "no_policy_evaluated": True,
        }
        evidence = {
            "governance_prepared": True,
            "permissions_requested_count": len(req["permissions"]),
            "policies_count": len(req["policies"]),
            "approval_mode": req["approvals"],
            "no_policy_evaluated": True,
        }
        return req, evidence

    def _prepare_workspace(self, mission: Mission) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare Workspace Runtime configuration without filesystem writes."""
        ws_root = mission.context.workspace_root
        oniroute_dir = ws_root / ".oniroute"

        canonical_subdirs = [
            "sessions", "history", "traces", "artifacts", "generated",
            "temporary", "reports", "approvals", "cache", "logs",
            "memory", "context", "knowledge", "runtime", "locks", "plans"
        ]

        directories = {name: str(oniroute_dir / name) for name in canonical_subdirs}

        req = {
            "workspace_root": str(ws_root),
            "engine_root": str(mission.context.engine_root),
            "storage_root": str(oniroute_dir),
            "history_root": directories["history"],
            "reports_root": directories["reports"],
            "artifacts_root": directories["artifacts"],
            "sessions_root": directories["sessions"],
            "execution_directories": directories,
            "status": "PREPARED",
            "no_filesystem_writes": True,
        }
        evidence = {
            "workspace_prepared": True,
            "canonical_directories_count": len(canonical_subdirs),
            "read_only_engine_asserted": mission.context.read_only_engine_confirmed,
            "no_filesystem_writes": True,
        }
        return req, evidence

    def _prepare_umal(self, mission: Mission) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare ModelRequest payload for UMAL without model selection."""
        params = mission.request.parameters or {}
        req = {
            "mission_id": mission.mission_id,
            "capabilities_required": mission.requirements.target_artifacts,
            "constraints": {
                "local_only": mission.constraints.local_only,
                "allowed_providers": mission.constraints.allowed_providers,
                "max_budget_usd": mission.constraints.max_budget_usd,
            },
            "preferences": {
                "preferred_provider": params.get("preferred_provider"),
                "local_preference": mission.constraints.local_only,
            },
            "provider_independence": True,
            "status": "PREPARED",
            "no_model_selected": True,
        }
        evidence = {
            "umal_prepared": True,
            "target_artifacts": mission.requirements.target_artifacts,
            "local_only": mission.constraints.local_only,
            "provider_independence": True,
            "no_model_selected": True,
        }
        return req, evidence

    def _prepare_invocation(self, mission: Mission) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare InvocationRequest payload without executing invocation."""
        params = mission.request.parameters or {}
        now_str = datetime.now(timezone.utc).isoformat()

        req = {
            "mission_id": mission.mission_id,
            "streaming": params.get("streaming", False),
            "tracing": True,
            "callbacks": ["event_bus", "artifact_router", "trace_storage"],
            "execution_metadata": {
                "mission_id": mission.mission_id,
                "prepared_at": now_str,
            },
            "status": "PREPARED",
            "no_invocation": True,
        }
        evidence = {
            "invocation_prepared": True,
            "streaming": req["streaming"],
            "tracing": True,
            "callbacks_count": len(req["callbacks"]),
            "no_invocation_executed": True,
        }
        return req, evidence
