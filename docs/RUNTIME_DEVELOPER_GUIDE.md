# Agent Runtime Developer Guide (ACR-006 Phase R5)

This guide provides technical instructions for software engineers integrating or building on top of the **OniRoute Agent Runtime**.

---

## 1. Runtime Architecture & Package Structure

The Agent Runtime is located under `runtime/agent/`:

```
runtime/agent/
├── models.py                # Pydantic data schemas & FSM transition rules
├── contracts.py             # Abstract Base Class (ABC) interface specifications
├── session_manager.py       # Session FSM lifecycle manager
├── session_coordinator.py   # Blueprint session initialization coordinator
├── session_registry.py      # In-memory registry for active AgentSession instances
├── runtime_initializer.py   # Blueprint → RuntimeContext initialization
├── execution_engine.py      # Core execution engine (Governance + UMAL + Invocation)
├── artifact_collector.py    # Artifact registration & lineage collector
├── event_recorder.py        # Event log recorder
├── execution_reporter.py    # Execution result report compiler
└── recovery/                # Recovery & Human Review subsystem
    ├── classifier.py        # FailureClassifier (8 categories)
    ├── events.py            # RecoveryEventType enum
    ├── models.py            # Immutable recovery Pydantic models
    ├── retry.py             # RetryManager & exponential backoff
    ├── review.py            # RuntimeReviewEngine
    ├── policy.py            # Declarative ReviewPolicy contracts & presets
    └── orchestrator.py      # RecoveryOrchestrator lifecycle coordinator
```

---

## 2. Instantiating Sessions Programmatically

```python
from pathlib import Path
from runtime.mission import MissionIntake, MissionResolver, MissionOrchestrator
from runtime.organization import ExecutionBlueprintAssembler
from runtime.agent import SessionCoordinator

repo_root = Path.cwd()

# 1. Pipeline: Intake → Resolve → Orchestrate → Assemble Blueprint
intake = MissionIntake()
req = intake.process_intake("Build REST API endpoints")
resolver = MissionResolver()
mission = resolver.resolve_mission(req)
orchestrator = MissionOrchestrator()
exec_req = orchestrator.orchestrate_mission(mission)
assembler = ExecutionBlueprintAssembler(repository_root=repo_root)
blueprint = assembler.assemble_blueprint(exec_req, repository_root=repo_root)

# 2. Initialize Agent Sessions
coordinator = SessionCoordinator()
context, sessions, report = coordinator.initialize_sessions(blueprint)

print(f"Initialized {len(sessions)} sessions for blueprint {blueprint.blueprint_id}")
```

---

## 3. Executing Agent Sessions

```python
from runtime.agent import AgentExecutionEngine

engine = AgentExecutionEngine(repository_root=repo_root)

# Execute all READY sessions sequentially
results, runtime_report = engine.execute_all(blueprint, coordinator.registry)

print(f"Completed {runtime_report.completed_sessions} of {runtime_report.total_sessions} sessions")
```

---

## 4. Programmatic Recovery & Review Management

```python
from runtime.agent.recovery import (
    RecoveryOrchestrator,
    FailureClassifier,
    ReviewDecision,
    RetryPolicy,
    SECURITY_POLICY,
)

# 1. Instantiate RecoveryOrchestrator with policy
orchestrator = RecoveryOrchestrator(
    retry_policy=RetryPolicy(max_retries=3, base_delay_seconds=1.0)
)

session = sessions[0]

# 2. Pause & Resume
session, pause_record = orchestrator.pause(session, reason="Waiting for API token")
# ... after token received ...
session, closed_pause = orchestrator.resume(session)

# 3. Human Review Gate
session = orchestrator.request_review(session, reason="Database schema modification")
pending_id = orchestrator.review_engine.pending_review_ids[0]

# Submit approval decision
session = orchestrator.apply_review_decision(
    session,
    review_id=pending_id,
    decision=ReviewDecision.APPROVE,
    actor="lead-architect",
    notes="Schema reviewed and approved.",
)

# 4. Generate Recovery Report
report = orchestrator.generate_report(session, blueprint.blueprint_id, mission.mission_id)
print(report.model_dump_json(indent=2))
```

---

## 5. Extension Rules

1. **Do NOT mutate frozen models:** Recovery models use `frozen=True`.
2. **Preserve FSM rules:** State transitions must comply with `can_runtime_transition()`.
3. **Use custom ReviewPolicy:** To add custom review rules, implement `ReviewPolicy` protocol in `runtime/agent/recovery/policy.py`.
