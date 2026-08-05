"""Deterministic Execution Task Queue for Swarm Execution (Phase P3.A3).

Transforms RuntimeExecutionSnapshot into a deterministic, ordered ExecutionTaskQueue
without recalculating or reordering pre-planned dependencies.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from runtime.agent.models import ExecutionStatus
from .models import RuntimeExecutionSnapshot


class ExecutionTask(BaseModel):
    """Immutable task execution record generated from RuntimeExecutionSnapshot."""

    model_config = ConfigDict(frozen=True)

    task_id: str = Field(..., description="Unique execution task identifier (e.g. task-w1-sess-devops-001)")
    wave_number: int = Field(..., ge=1, le=6, description="Wave number (1-6)")
    profile_id: str = Field(..., description="Associated AgentProfile ID")
    session_id: str = Field(..., description="Associated AgentSession ID")
    agent_role: str = Field(..., description="Human-readable agent role title")
    primary_discipline: str = Field(..., description="Primary engineering discipline")
    bundle_reference: str = Field(default="", description="Assigned skill bundle reference")
    dependencies: List[str] = Field(default_factory=list, description="Prerequisite task IDs")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="Execution status")
    retry_counter: int = Field(default=0, ge=0, description="Current retry attempt count")
    max_retries: int = Field(default=3, ge=0, description="Max allowed retries")
    timeout_seconds: int = Field(default=300, ge=1, description="Timeout limit in seconds")
    priority: int = Field(default=1, ge=1, description="Execution priority (1 highest)")
    execution_hash: str = Field(..., description="SHA-256 task execution hash")


class ExecutionTaskQueue:
    """Deterministic, immutable-ordering Execution Task Queue.

    Consumes a RuntimeExecutionSnapshot and constructs an ordered task queue
    without recalculating wave ordering or topological dependencies.
    """

    def __init__(self, tasks: List[ExecutionTask]) -> None:
        self._tasks: List[ExecutionTask] = list(tasks)
        self._task_map: Dict[str, ExecutionTask] = {t.task_id: t for t in tasks}

    @classmethod
    def from_snapshot(cls, snapshot: RuntimeExecutionSnapshot) -> ExecutionTaskQueue:
        """Construct a deterministic ExecutionTaskQueue from a RuntimeExecutionSnapshot."""
        tasks: List[ExecutionTask] = []
        profile_task_map: Dict[str, str] = {}

        # 1. First pass: Assign task IDs for profiles across ordered waves
        for w_num in range(1, 7):
            w_stat = snapshot.wave_status.get(w_num)
            if not w_stat or not w_stat.profile_ids:
                continue

            for pid in w_stat.profile_ids:
                sess_record = snapshot.session_map.get(pid)
                if not sess_record:
                    continue

                p_slug = sess_record.primary_discipline.lower().replace(" ", "-")
                task_id = f"task-w{w_num}-{p_slug}-{sess_record.session_id[:8]}"
                profile_task_map[pid] = task_id

        # 2. Second pass: Build ExecutionTask objects with prerequisite task IDs
        for w_num in range(1, 7):
            w_stat = snapshot.wave_status.get(w_num)
            if not w_stat or not w_stat.profile_ids:
                continue

            for pid in w_stat.profile_ids:
                sess_record = snapshot.session_map.get(pid)
                if not sess_record:
                    continue

                task_id = profile_task_map[pid]
                session_obj = next((s for s in snapshot.sessions if s.session_id == sess_record.session_id), None)
                bundle_ref = session_obj.capability_ids[0] if session_obj and session_obj.capability_ids else ""

                # Prerequisite task IDs from profile dependencies
                prereq_task_ids: List[str] = []

                # Find profile object in snapshot context or session map dependencies
                retry_limit = snapshot.retry_status.max_retry_limits.get(pid, 3)

                task_payload = {
                    "task_id": task_id,
                    "wave_number": w_num,
                    "profile_id": pid,
                    "session_id": sess_record.session_id,
                    "agent_role": sess_record.agent_role,
                    "primary_discipline": sess_record.primary_discipline,
                    "bundle_reference": bundle_ref,
                    "max_retries": retry_limit,
                }
                exec_hash = hashlib.sha256(
                    json.dumps(task_payload, sort_keys=True).encode("utf-8")
                ).hexdigest()

                task = ExecutionTask(
                    task_id=task_id,
                    wave_number=w_num,
                    profile_id=pid,
                    session_id=sess_record.session_id,
                    agent_role=sess_record.agent_role,
                    primary_discipline=sess_record.primary_discipline,
                    bundle_reference=bundle_ref,
                    dependencies=prereq_task_ids,
                    status=ExecutionStatus.PENDING,
                    retry_counter=0,
                    max_retries=retry_limit,
                    timeout_seconds=300,
                    priority=w_num,
                    execution_hash=exec_hash,
                )
                tasks.append(task)

        return cls(tasks)

    def get_all_tasks(self) -> List[ExecutionTask]:
        """Return all tasks in execution order."""
        return list(self._tasks)

    def get_tasks_for_wave(self, wave_number: int) -> List[ExecutionTask]:
        """Return tasks assigned to a specific wave number."""
        return [t for t in self._tasks if t.wave_number == wave_number]

    def get_task(self, task_id: str) -> Optional[ExecutionTask]:
        """Retrieve a task by its task ID."""
        return self._task_map.get(task_id)

    def __len__(self) -> int:
        return len(self._tasks)
