# Autonomous Swarm Developer Guide

## 1. Developer Quickstart

To run the complete Autonomous Swarm pipeline end-to-end:

```bash
# 1. Plan Mission Deployment (P3.A1)
oniroute deployment "Build a React FastAPI web application"

# 2. Initialize Swarm Execution State (P3.A2)
oniroute initialize "Build a React FastAPI web application"

# 3. Execute Swarm Waves Autonomously (P3.A3)
oniroute execute "Build a React FastAPI web application"

# 4. Coordinate Swarm Communication & Handoffs (P3.A4)
oniroute coordinate "Build a React FastAPI web application"
```

---

## 2. Python API Usage

```python
from runtime.deployment import MissionDeploymentPlanner
from runtime.swarm import (
    SwarmInitializationEngine,
    AutonomousExecutionEngine,
    SwarmCoordinationEngine,
    AutonomousSwarmCertificationEngine,
)

# 1. Mission Deployment Planning (P3.A1)
deployment_plan = MissionDeploymentPlanner().create_deployment_plan(exec_plan, profile_report)

# 2. Swarm Initialization (P3.A2)
init_snapshot = SwarmInitializationEngine().initialize_swarm(deployment_plan)

# 3. Autonomous Execution (P3.A3)
exec_snapshot, results = AutonomousExecutionEngine().execute_swarm(init_snapshot)

# 4. Swarm Coordination (P3.A4)
coord_snapshot, summary = SwarmCoordinationEngine().coordinate_swarm(exec_snapshot, results)

# 5. Certification Audit (P3.A5)
cert_report = AutonomousSwarmCertificationEngine().certify_subsystem()
assert cert_report["certified"] is True
```

---

## 3. Hand-off Contract for Code Generation (Phase P4.G1)

Phase P4.G1 begins **Code Generation**.

### Hand-off Contract for P4.G1:
- Consumes **ONLY** [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125) and generated execution artifacts.
- Begins deterministic source code generation targeting workspace project structure.
- **Strict Prohibition**: No planning, no execution redesign, no swarm redesign!
