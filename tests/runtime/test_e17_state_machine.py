"""E1.7.3 TaskState lifecycle freeze verification.

Verifies the frozen TaskState machine:
Queued -> Ready -> Running -> Completed | Failed | Blocked | Skipped | Cancelled
(+ Waiting as an intermediate state)
"""

from __future__ import annotations

import pytest

from runtime.engineering import InvocationTask, TaskContext, TaskState


def _task(state=TaskState.QUEUED):
    return InvocationTask(
        task_id="t1", contract_id="c1", target_path="src/app.py",
        execution_context=TaskContext(
            engineering_contract_id="c1", execution_batch_id="b1", invocation_task_id="t1"
        ),
        state=state,
    )


def test_valid_transitions():
    """Verify every documented valid transition."""
    # Queued -> Ready
    t = _task().transition_to(TaskState.READY)
    assert t.state == TaskState.READY
    # Ready -> Running
    t = t.transition_to(TaskState.RUNNING)
    assert t.state == TaskState.RUNNING
    # Running -> Completed
    assert t.transition_to(TaskState.COMPLETED).state == TaskState.COMPLETED


def test_waiting_is_intermediate():
    """Waiting is a valid intermediate from Running/Ready, and returns to Running."""
    # Ready -> Waiting
    t = _task(TaskState.READY).transition_to(TaskState.WAITING)
    assert t.state == TaskState.WAITING
    # Waiting -> Running
    assert t.transition_to(TaskState.RUNNING).state == TaskState.RUNNING
    # Running -> Waiting
    assert _task(TaskState.RUNNING).transition_to(TaskState.WAITING).state == TaskState.WAITING


def test_invalid_transitions_rejected():
    """Invalid transitions raise ValueError."""
    # Queued cannot go directly to Running/Completed/Failed.
    for bad in (TaskState.RUNNING, TaskState.COMPLETED, TaskState.FAILED):
        with pytest.raises(ValueError):
            _task(TaskState.QUEUED).transition_to(bad)
    # Ready cannot go directly to Completed.
    with pytest.raises(ValueError):
        _task(TaskState.READY).transition_to(TaskState.COMPLETED)


def test_terminal_states_are_terminal():
    """Terminal states reject any transition."""
    for terminal in (TaskState.COMPLETED, TaskState.FAILED, TaskState.BLOCKED, TaskState.SKIPPED, TaskState.CANCELLED):
        for target in (TaskState.RUNNING, TaskState.READY, TaskState.QUEUED):
            with pytest.raises(ValueError):
                _task(terminal).transition_to(target)


def test_serialization_stability():
    """TaskState enum serializes deterministically."""
    assert TaskState.QUEUED.value == "Queued"
    assert TaskState.READY.value == "Ready"
    assert TaskState.RUNNING.value == "Running"
    assert TaskState.WAITING.value == "Waiting"
    assert TaskState.COMPLETED.value == "Completed"
    assert TaskState.FAILED.value == "Failed"
    assert TaskState.BLOCKED.value == "Blocked"
    assert TaskState.SKIPPED.value == "Skipped"
    assert TaskState.CANCELLED.value == "Cancelled"


def test_state_enum_deterministic_ordering():
    """Enum member ordering is stable (does not change between runs)."""
    members = list(TaskState)
    assert members[0] == TaskState.QUEUED
    assert members[1] == TaskState.READY
    assert members[2] == TaskState.RUNNING
    assert members[3] == TaskState.WAITING
