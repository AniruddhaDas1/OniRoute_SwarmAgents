# Phase P3.A2 — Session Initialization Specification

## 1. Agent Session Instantiation Rules

In Phase P3.A2, every scheduled [`AgentProfile`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L164) in the [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) is bound to exactly **One Runtime Session**.

```
AgentProfile ──► SwarmInitializationEngine ──► AgentSession (State: READY)
```

---

## 2. Session Lifecycle State Mapping

All sessions are created in state **`READY`**:

```
INITIALIZED ──► READY (Initial Swarm State) ──► RUNNING (Phase P3.A3)
```

- **`RuntimeState`**: `RuntimeState.READY`
- **`ExecutionStatus`**: `ExecutionStatus.PENDING`
- **Events Log**: Contains initial `SESSION_CREATED` event capturing transition from `INITIALIZED` to `READY`.
- **Metrics**: Initialized `RuntimeMetrics(start_time=now_str, artifact_count=0, event_count=1, retry_count=0)`.

---

## 3. Session Attributes & Bindings

Each instantiated [`AgentSession`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/agent/models.py#L184) contains:

| Attribute | Source / Value |
|---|---|
| `session_id` | `sess-{discipline}-{hash}` |
| `member_id` | `mem-{discipline}` |
| `role_id` | `role-{discipline}` |
| `role_title` | `profile.agent_role` |
| `blueprint_id` | `bp-{execution_plan_id}` |
| `capability_ids` | `profile.assigned_bundle_references` |
| `required_skills` | `profile.knowledge_references` |
| `knowledge_references` | `profile.knowledge_references` |
| `package_references` | `profile.package_references` |
| `workflow_references` | `profile.workflow_references` |
| `execution_constraints` | Transformed from `profile.execution_constraints` |
| `state` | `RuntimeState.READY` |
| `status` | `ExecutionStatus.PENDING` |
| `artifacts` | `[]` (Empty — zero artifacts generated during initialization) |
| `events` | `[SESSION_CREATED]` |
