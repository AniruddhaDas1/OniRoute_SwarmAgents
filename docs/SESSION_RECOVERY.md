# Session Recovery & Status Specification (Phase P6.D2)

## 1. Overview

The [`SessionRecoveryWatcher`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/experience/recovery.py#L16) enables session recovery and status monitoring from workspace storage (`.oniroute/sessions/`, `.oniroute/traces/`).

---

## 2. CLI Commands

### Session Status Command (`oniroute status`)
Displays the status, progress, quality score, production readiness, and active agent for a session:
```bash
oniroute status
oniroute status --session sess-123456
oniroute status --json
```

### Live Watch Command (`oniroute watch`)
Streams live execution events from active or past session traces:
```bash
oniroute watch
oniroute watch --session sess-123456
```
