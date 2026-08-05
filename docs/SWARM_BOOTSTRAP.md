# Phase P3.A2 — Swarm Bootstrap Guide

## 1. Quickstart

To initialize swarm execution state from a deployment plan:

```bash
oniroute initialize "Build a React FastAPI web application"
```

To output the raw JSON [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125):

```bash
oniroute initialize "Build a React FastAPI web application" --json
```

---

## 2. Python API Usage

```python
from runtime.deployment import MissionDeploymentPlanner
from runtime.swarm import SwarmInitializationEngine, benchmark_swarm_initialization

# 1. Obtain MissionDeploymentPlan from P3.A1
planner = MissionDeploymentPlanner()
deployment_plan = planner.create_deployment_plan(exec_plan, profile_report)

# 2. Initialize Swarm Execution State (P3.A2)
swarm_engine = SwarmInitializationEngine()
snapshot = swarm_engine.initialize_swarm(deployment_plan)

print(f"Execution UUID: {snapshot.execution_uuid}")
print(f"Snapshot Hash: {snapshot.snapshot_hash}")
print(f"Sessions Initialized: {len(snapshot.sessions)}")
print(f"Initial Execution State: {snapshot.execution_cursor.execution_state}")

# 3. Benchmark Performance & Determinism
bench = benchmark_swarm_initialization(swarm_engine, deployment_plan, iterations=100)
print(f"Is Deterministic: {bench['is_deterministic']}")
print(f"Average Latency: {bench['repeat_avg_latency_ms']} ms")
```

---

## 3. Hand-off Contract for Autonomous Execution (Phase P3.A3)

Swarm Initialization **prepares execution**. It does NOT execute code, invoke LLMs, or generate artifacts.

### Hand-off Contract for P3.A3:
- Consumes **ONLY** [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125).
- Responsibility of P3.A3: Transition sessions from `READY` to `RUNNING`, invoke AI models/tools according to plan policies, collect generated artifacts, log execution traces, enforce review/approval gates, and advance execution cursor across Waves 1 to 6.
- Only in Phase P3.A3 may runtime execution begin!
