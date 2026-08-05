# Phase P3.A3 — Runtime Execution Guide

## 1. Quickstart

To run autonomous swarm execution across Waves 1 to 6:

```bash
# Execute swarm execution waves autonomously
oniroute execute "Build a React FastAPI web application"

# Output raw JSON snapshot and task execution results
oniroute execute "Build a React FastAPI web application" --json
```

---

## 2. Python API Usage

```python
from runtime.deployment import MissionDeploymentPlanner
from runtime.swarm import (
    SwarmInitializationEngine,
    AutonomousExecutionEngine,
    benchmark_autonomous_execution,
)

# 1. Initialize Swarm Execution State (Phase P3.A2)
swarm_init_engine = SwarmInitializationEngine()
initial_snapshot = swarm_init_engine.initialize_swarm(deployment_plan)

# 2. Execute Swarm Autonomously (Phase P3.A3)
exec_engine = AutonomousExecutionEngine()
updated_snapshot, results = exec_engine.execute_swarm(initial_snapshot)

print(f"Final State: {updated_snapshot.execution_cursor.execution_state}")
print(f"Tasks Executed: {len(results)}")
print(f"Spent USD: ${updated_snapshot.budget_status.spent_budget_usd:.4f}")
print(f"Remaining USD: ${updated_snapshot.budget_status.remaining_budget_usd:.2f}")

# 3. Benchmark Execution Performance & Token Throughput
bench = benchmark_autonomous_execution(exec_engine, initial_snapshot, iterations=20)
print(f"Tokens/sec: {bench['tokens_per_sec']}")
print(f"Artifacts/sec: {bench['artifacts_per_sec']}")
print(f"Is Deterministic: {bench['is_deterministic']}")
```

---

## 3. Hand-off Contract for Swarm Coordination (Phase P3.A4)

Autonomous Execution **executes work**. It does NOT handle complex agent-to-agent communication, consensus, or handoffs.

### Hand-off Contract for P3.A4:
- Consumes updated [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125) and execution results.
- Responsibility of P3.A4: Agent-to-agent communication, shared context updates, handoff protocols, multi-agent consensus, and conflict resolution across active sessions.
- Execution logic must remain unchanged in Phase P3.A4!
