# Phase P3.A1 — Mission Deployment Guide

## 1. Quickstart

To generate a deterministic Mission Deployment Plan from natural language input:

```bash
oniroute deployment "Build a React FastAPI web application"
```

To output raw JSON for integration into downstream tools or P3.A2 Swarm Initialization:

```bash
oniroute deployment "Build a React FastAPI web application" --json
```

---

## 2. Python API Guide

```python
from runtime.deployment import MissionDeploymentPlanner, benchmark_deployment_planner
from runtime.workspace.plan import EngineeringPlanGenerator
from runtime.skills import AgentProfileBuilderEngine, SkillDiscoveryEngine, SkillRankingEngine, SkillBundlingEngine

# 1. Generate EngineeringExecutionPlan
plan_gen = EngineeringPlanGenerator()
exec_plan = plan_gen.generate_plan(intent_report, ws_context, repo_context)

# 2. Synthesize AgentProfileReport
discovery_engine = SkillDiscoveryEngine(registry, resolver)
selection_report = discovery_engine.discover_skills(exec_plan)

ranking_engine = SkillRankingEngine(registry, resolver)
ranked_report = ranking_engine.rank_skills(selection_report, exec_plan)

bundling_engine = SkillBundlingEngine(registry, resolver)
bundle_report = bundling_engine.bundle_skills(ranked_report, exec_plan, selection_report)

builder_engine = AgentProfileBuilderEngine(registry, resolver)
profile_report = builder_engine.build_profiles(bundle_report, exec_plan)

# 3. Create MissionDeploymentPlan
planner = MissionDeploymentPlanner()
deployment_plan = planner.create_deployment_plan(exec_plan, profile_report)

# 4. Measure performance & determinism
benchmarks = benchmark_deployment_planner(planner, exec_plan, profile_report, iterations=100)
print(f"Deployment Hash: {deployment_plan.deployment_hash}")
print(f"Is Deterministic: {benchmarks['is_deterministic']}")
```

---

## 3. Transition to Swarm Initialization (P3.A2)

The Mission Deployment Planner **prepares execution**. It does NOT execute code, create sessions, or instantiate AI models.

### Hand-off Contract for P3.A2:
- Consumes **ONLY** [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180).
- Responsibility of P3.A2: Instantiate runtime sessions, allocate execution context, prepare execution state, and initialize the swarm.
- P3.A2 must NOT execute any work yet.
