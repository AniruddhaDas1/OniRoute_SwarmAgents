# Mission Inspection Reference — Phase P6.D3

## Overview

Mission Inspection provides a detailed snapshot of any running, paused, or completed
mission's current state. It reads from Trace Storage and the in-memory mission
registry without modifying any Runtime behavior.

## Inspection Data

| Field | Description | Source |
|---|---|---|
| `mission_id` | Unique mission identifier | Command parameter |
| `session_id` | Associated session | SessionStorage |
| `status` | Current mission state | Mission registry / TraceStorage |
| `current_stage` | Active pipeline stage | Last trace event |
| `current_agent` | Active agent profile | Last trace event |
| `current_contract` | Active engineering contract | Last trace event payload |
| `files_created` | Files created so far | Last trace event |
| `files_modified` | Files modified so far | Last trace event |
| `quality_score` | Current quality score | Last trace event |
| `token_usage` | Token consumption map | Last trace event |
| `estimated_cost_usd` | Estimated cost in USD | Last trace event |
| `active_mcp_tools` | Active MCP tool names | Last trace event payload |
| `remaining_contracts` | Remaining contracts count | Last trace event payload |
| `progress_percentage` | Overall progress | Last trace event |
| `production_ready` | Production readiness flag | Last trace event |
| `elapsed_time_ms` | Elapsed execution time | Last trace event |

## CLI Usage

```bash
# Inspect latest mission
oniroute inspect

# Inspect specific mission
oniroute inspect --mission msn-abc-123

# JSON output for scripting
oniroute inspect --json
```

## Programmatic Usage

```python
from runtime.control import MissionControlEngine

engine = MissionControlEngine(workspace_root=Path("/my/project"))
inspection = engine.inspect_mission("msn-abc-123")

print(f"Stage: {inspection.current_stage}")
print(f"Agent: {inspection.current_agent}")
print(f"Progress: {inspection.progress_percentage}%")
print(f"Quality: {inspection.quality_score}")
print(f"Files: {len(inspection.files_created)} created")
print(f"Cost: ${inspection.estimated_cost_usd:.4f}")
print(f"Tools: {', '.join(inspection.active_mcp_tools)}")
```

## Inspection Targets

| Target | What You See |
|---|---|
| Current Agent | Which agent profile is currently executing |
| Current Stage | Which pipeline stage is active (ENGINEERING, REVIEW, HEALING) |
| Generated Artifacts | List of files created and modified |
| Current Cost | Accumulated estimated cost in USD |
| Current Tokens | Token consumption breakdown |
| Active MCP Tools | Which MCP tools are being used |
| Remaining Work | Number of remaining engineering contracts |

## Constraints

- Inspection is read-only and never modifies mission state
- Inspection reads from TraceStorage and in-memory registry
- Inspection latency target: < 100ms
