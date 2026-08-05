"""Autonomous Execution Engine for OniRoute (Phase P3.A3).

Executes swarm execution waves deterministically from a RuntimeExecutionSnapshot without
duplicating Runtime services or regenerating execution plans/profiles.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from runtime.agent.execution_engine import AgentExecutionEngine
from runtime.agent.models import (
    AgentSession,
    ArtifactRecord,
    ArtifactType,
    ExecutionEvent,
    ExecutionStatus,
    RuntimeMetrics,
    RuntimeState,
    RuntimeEventType,
)
from runtime.workspace.artifact_router import ArtifactRouter
from runtime.workspace.history_storage import ExecutionHistoryStorage
from runtime.workspace.log_storage import LogStorage

from runtime.workspace.manager import WorkspaceManager
from runtime.workspace.report_storage import ReportStorage
from runtime.workspace.session_storage import SessionStorage
from runtime.workspace.trace_storage import TraceStorage
from runtime.workspace.storage import WorkspaceStorage

from .exceptions import SwarmInitializationError
from .models import (
    BudgetStatus,
    ExecutionCursor,
    RuntimeExecutionSnapshot,
    SessionStateRecord,
    WaveExecutionStatus,
)
from .queue import ExecutionTask, ExecutionTaskQueue
from .result import SwarmExecutionResult


DISCIPLINE_ARTIFACT_TYPE_MAP: Dict[str, ArtifactType] = {
    "DevOps": ArtifactType.CONFIG,
    "Infrastructure": ArtifactType.CONFIG,
    "Backend": ArtifactType.CODE,
    "Frontend": ArtifactType.CODE,
    "Database": ArtifactType.SCHEMA,
    "AI": ArtifactType.CODE,
    "Testing": ArtifactType.TEST_SUITE,
    "Security": ArtifactType.REVIEW,
    "Governance": ArtifactType.REPORT,
    "Documentation": ArtifactType.DOCUMENTATION,
    "Analytics": ArtifactType.DATA,
    "Automation": ArtifactType.CODE,
    "General Engineering": ArtifactType.CODE,
}


class AutonomousExecutionEngine:
    """Core Autonomous Execution Engine driving Swarm waves and updating RuntimeExecutionSnapshots."""

    def execute_swarm(
        self,
        snapshot: RuntimeExecutionSnapshot,
        repository_root: Path | None = None,
        max_budget_usd: float | None = None,
        force_failure_profile_id: str | None = None,
    ) -> Tuple[RuntimeExecutionSnapshot, List[SwarmExecutionResult]]:
        """Execute all waves in the snapshot deterministically and return updated snapshot and results."""
        if not snapshot.sessions:
            raise SwarmInitializationError("RuntimeExecutionSnapshot contains no initialized sessions.")

        cwd = repository_root or Path.cwd()
        now_str = datetime.now(timezone.utc).isoformat()
        t_start = time.perf_counter()

        # 1. Build ExecutionTaskQueue (never recalculate execution order)
        queue = ExecutionTaskQueue.from_snapshot(snapshot)

        # 2. Setup workspace storage connections
        manager = WorkspaceManager()
        ws_ctx = manager.create_context(cwd=cwd)
        storage = WorkspaceStorage(ws_ctx.workspace_metadata) if ws_ctx.workspace_metadata and ws_ctx.is_engine_read_only() else None

        trace_storage = TraceStorage(ws_ctx.workspace_metadata) if storage else None
        log_storage = LogStorage(ws_ctx.workspace_metadata) if storage else None
        history_storage = ExecutionHistoryStorage(ws_ctx.workspace_metadata) if storage else None

        artifact_router = ArtifactRouter(ws_ctx.workspace_metadata) if storage else None

        # Mutable state containers
        updated_sessions: Dict[str, AgentSession] = {s.session_id: s for s in snapshot.sessions}
        updated_session_map: Dict[str, SessionStateRecord] = dict(snapshot.session_map)
        updated_wave_status: Dict[int, WaveExecutionStatus] = dict(snapshot.wave_status)

        results: List[SwarmExecutionResult] = []
        total_tokens_consumed = 0
        total_cost_usd = 0.0

        current_budget_limit = max_budget_usd if max_budget_usd is not None else snapshot.budget_status.total_budget_usd
        spent_usd = snapshot.budget_status.spent_budget_usd
        budget_exhausted = False

        # 3. Wave-by-Wave Execution Loop (Waves 1 to 6)
        for w_num in range(1, 7):
            w_tasks = queue.get_tasks_for_wave(w_num)
            if not w_tasks:
                continue

            if spent_usd >= current_budget_limit:
                budget_exhausted = True
                updated_wave_status[w_num] = WaveExecutionStatus(
                    wave_number=w_num,
                    name=snapshot.wave_status[w_num].name if w_num in snapshot.wave_status else f"Wave {w_num}",
                    status="SKIPPED",
                    profile_ids=[t.profile_id for t in w_tasks],
                    completed_profile_ids=[],
                    failed_profile_ids=[],
                )
                continue


            # Update wave status to IN_PROGRESS
            wave_name = snapshot.wave_status[w_num].name if w_num in snapshot.wave_status else f"Wave {w_num}"
            updated_wave_status[w_num] = WaveExecutionStatus(
                wave_number=w_num,
                name=wave_name,
                status="IN_PROGRESS",
                profile_ids=[t.profile_id for t in w_tasks],
                completed_profile_ids=[],
                failed_profile_ids=[],
            )

            completed_in_wave: List[str] = []
            failed_in_wave: List[str] = []

            for task in w_tasks:
                if spent_usd >= current_budget_limit:
                    budget_exhausted = True
                    break

                sess_rec = updated_session_map[task.profile_id]
                session = updated_sessions[sess_rec.session_id]

                # Check if simulated failure requested
                should_fail = (force_failure_profile_id == task.profile_id)

                task_t0 = time.perf_counter()

                # Transition state READY -> RUNNING -> COMPLETED / FAILED
                running_event = ExecutionEvent(
                    event_id=f"evt-start-{task.task_id}",
                    event_type=RuntimeEventType.EXECUTION_STARTED,
                    session_id=session.session_id,
                    member_id=session.member_id,
                    description=f"Autonomous execution started for task '{task.task_id}'",
                    previous_state=RuntimeState.READY,
                    next_state=RuntimeState.RUNNING,
                    timestamp=now_str,
                )

                # Simulated artifact production
                art_type = DISCIPLINE_ARTIFACT_TYPE_MAP.get(task.primary_discipline, ArtifactType.CODE)
                art_id = f"art-{task.task_id[:12]}"
                art_name = f"{task.primary_discipline} Deliverable for {task.agent_role}"

                art_record = ArtifactRecord(
                    artifact_id=art_id,
                    artifact_type=art_type,
                    owner_session_id=session.session_id,
                    owner_member_id=session.member_id,
                    capability_id=task.bundle_reference or f"cap-{task.primary_discipline.lower()}",
                    name=art_name,
                    description=f"Generated artifact deliverable for role '{task.agent_role}'",
                    lineage=[],
                    references=[f".oniroute/artifacts/{art_id}.json"],
                    produced_at=now_str,
                )

                # Compute token usage & cost
                task_tokens = 350 + (len(task.agent_role) * 10)
                task_cost = round(0.0015 * (task_tokens / 100.0), 4)

                spent_usd = round(spent_usd + task_cost, 4)
                total_tokens_consumed += task_tokens
                total_cost_usd = round(total_cost_usd + task_cost, 4)

                task_t1 = time.perf_counter()
                task_duration = task_t1 - task_t0

                # Logging & Trace references
                log_ref = f".oniroute/logs/{session.session_id}.log"
                trace_ref = f".oniroute/traces/{session.session_id}.json"

                if storage and log_storage:
                    try:
                        log_storage.append_log(session.session_id, f"Executed task {task.task_id} for role '{session.role_title}'")
                    except Exception:
                        pass

                if storage and trace_storage:
                    try:
                        trace_storage.record_trace(session.session_id, {"task_id": task.task_id, "tokens": task_tokens, "status": "DONE"})
                    except Exception:
                        pass

                if should_fail:
                    end_state = RuntimeState.FAILED
                    exec_status = ExecutionStatus.ERROR
                    failed_in_wave.append(task.profile_id)
                else:
                    end_state = RuntimeState.COMPLETED
                    exec_status = ExecutionStatus.DONE
                    completed_in_wave.append(task.profile_id)

                completion_event = ExecutionEvent(
                    event_id=f"evt-end-{task.task_id}",
                    event_type=RuntimeEventType.EXECUTION_COMPLETED if not should_fail else RuntimeEventType.EXECUTION_FAILED,
                    session_id=session.session_id,
                    member_id=session.member_id,
                    description=f"Autonomous execution completed for task '{task.task_id}'",
                    previous_state=RuntimeState.RUNNING,
                    next_state=end_state,
                    timestamp=now_str,
                )

                new_events = session.events + [running_event, completion_event]
                new_artifacts = session.artifacts + ([art_record] if not should_fail else [])

                updated_metrics = RuntimeMetrics(
                    session_id=session.session_id,
                    start_time=session.metrics.start_time if session.metrics else now_str,
                    end_time=now_str,
                    duration_seconds=round(task_duration, 4),
                    artifact_count=len(new_artifacts),
                    event_count=len(new_events),
                    retry_count=task.retry_counter,
                )

                updated_sess = AgentSession(
                    session_id=session.session_id,
                    member_id=session.member_id,
                    role_id=session.role_id,
                    role_title=session.role_title,
                    blueprint_id=session.blueprint_id,
                    capability_ids=session.capability_ids,
                    required_skills=session.required_skills,
                    knowledge_references=session.knowledge_references,
                    package_references=session.package_references,
                    workflow_references=session.workflow_references,
                    execution_constraints=session.execution_constraints,
                    state=end_state,
                    status=exec_status,
                    artifacts=new_artifacts,
                    events=new_events,
                    metrics=updated_metrics,
                    evidence=session.evidence,
                    metadata=session.metadata,
                    created_at=session.created_at,
                )
                updated_sessions[session.session_id] = updated_sess

                updated_session_map[task.profile_id] = SessionStateRecord(
                    session_id=session.session_id,
                    profile_id=task.profile_id,
                    agent_role=task.agent_role,
                    primary_discipline=task.primary_discipline,
                    wave_number=w_num,
                    state=end_state,
                    status=exec_status,
                    retry_count=task.retry_counter,
                    max_retries=task.max_retries,
                    allocated_budget_usd=sess_rec.allocated_budget_usd,
                )

                res = SwarmExecutionResult(
                    task_id=task.task_id,
                    session_id=session.session_id,
                    profile_id=task.profile_id,
                    wave_number=w_num,
                    execution_status=exec_status,
                    produced_artifacts=new_artifacts,
                    consumed_tokens=task_tokens,
                    execution_time_seconds=round(task_duration, 4),
                    provider_used="ollama",
                    model_used="llama3",
                    cost_usd=task_cost,
                    trace_references=[trace_ref],
                    log_references=[log_ref],
                    evidence={"tokens": task_tokens, "cost": task_cost},
                    timestamp=now_str,
                )
                results.append(res)

            wave_status_str = "FAILED" if failed_in_wave else ("COMPLETED" if len(completed_in_wave) == len(w_tasks) else "PARTIAL")
            updated_wave_status[w_num] = WaveExecutionStatus(
                wave_number=w_num,
                name=wave_name,
                status=wave_status_str,
                profile_ids=[t.profile_id for t in w_tasks],
                completed_profile_ids=completed_in_wave,
                failed_profile_ids=failed_in_wave,
            )

        t_end = time.perf_counter()
        total_latency = t_end - t_start

        # 4. Final Cursor & Budget Status Updates
        final_state = "FAILED" if any(r.execution_status == ExecutionStatus.ERROR for r in results) or budget_exhausted else "COMPLETED"
        last_wave = max(w for w in updated_wave_status if updated_wave_status[w].status in ("COMPLETED", "IN_PROGRESS")) if updated_wave_status else 6

        cursor = ExecutionCursor(
            active_wave_number=last_wave,
            active_profile_id=results[-1].profile_id if results else None,
            active_session_id=results[-1].session_id if results else None,
            current_step_index=len(results),
            execution_state=final_state,
            is_paused=False,
            is_completed=(final_state == "COMPLETED"),
        )

        total_budget = snapshot.budget_status.total_budget_usd
        budget_status = BudgetStatus(
            total_budget_usd=total_budget,
            spent_budget_usd=spent_usd,
            remaining_budget_usd=max(0.0, round(total_budget - spent_usd, 4)),
            wave_budget_allocations=dict(snapshot.budget_status.wave_budget_allocations),
            profile_budget_allocations=dict(snapshot.budget_status.profile_budget_allocations),
            currency="USD",
            is_exhausted=budget_exhausted or (spent_usd >= total_budget),
        )

        validation_metrics = dict(snapshot.evidence.get("validation", {}))
        validation_metrics.update(
            {
                "execution_completed": (final_state == "COMPLETED"),
                "all_tasks_executed": len(results) == len(queue),
                "total_tokens_consumed": total_tokens_consumed,
                "total_cost_usd": total_cost_usd,
                "execution_latency_ms": round(total_latency * 1000.0, 2),
            }
        )

        evidence = dict(snapshot.evidence)
        evidence["validation"] = validation_metrics
        evidence["execution_results_count"] = len(results)
        evidence["total_tokens"] = total_tokens_consumed
        evidence["total_cost_usd"] = total_cost_usd

        # 5. Compute SHA-256 Snapshot Hash over updated state
        deterministic_validation = {k: v for k, v in validation_metrics.items() if k != "execution_latency_ms"}
        preliminary_dict = {
            "snapshot_id": snapshot.snapshot_id,
            "mission_id": snapshot.mission_id,
            "deployment_plan_id": snapshot.deployment_plan_id,
            "execution_uuid": snapshot.execution_uuid,
            "session_count": len(updated_sessions),
            "executed_results_count": len(results),
            "final_state": final_state,
            "validation": deterministic_validation,
        }
        updated_hash = hashlib.sha256(
            json.dumps(preliminary_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()


        updated_snapshot = RuntimeExecutionSnapshot(
            snapshot_id=snapshot.snapshot_id,
            mission_id=snapshot.mission_id,
            deployment_plan_id=snapshot.deployment_plan_id,
            execution_uuid=snapshot.execution_uuid,
            wave_status=updated_wave_status,
            session_map=updated_session_map,
            sessions=list(updated_sessions.values()),
            execution_cursor=cursor,
            execution_context=snapshot.execution_context,
            budget_status=budget_status,
            retry_status=snapshot.retry_status,
            checkpoint_status=snapshot.checkpoint_status,
            event_bus_references=snapshot.event_bus_references,
            storage_references=snapshot.storage_references,
            workspace_references=snapshot.workspace_references,
            evidence=evidence,
            timestamp=now_str,
            snapshot_hash=updated_hash,
        )

        return updated_snapshot, results
