# OniRoute Mission Orchestrator User Guide (`docs/MISSION_USER_GUIDE.md`)

## Overview

The **OniRoute Mission Orchestrator** is an architecture-first framework for transforming natural language prompts and CLI instructions into validated, orchestrated execution requests without running AI models or executing code prematurely.

---

## Quick Start CLI Commands

### 1. Natural Language Handoff
Pass any natural language prompt directly to `oniroute`. The CLI automatically parses, resolves, and orchestrates the request:

```bash
oniroute "Create a premium SaaS landing page for an AI developer platform"
```

Output: A complete JSON-formatted `ExecutionRequest` payload in `ORCHESTRATED` state.

---

### 2. Inspecting Mission Status (`oniroute mission`)
Inspect workspace status and resolve user intent into a validated `Mission`:

```bash
oniroute mission "Build a REST API with FastAPI and PostgreSQL"
```

Add `--json` for raw JSON representation:

```bash
oniroute mission "Build a REST API with FastAPI and PostgreSQL" --json
```

---

### 3. Orchestrating a Mission (`oniroute mission orchestrate`)
Prepares all runtime execution payloads (`PlanningRequest`, `GovernanceRequest`, `Workspace`, `UMAL`, `Invocation`) without executing:

```bash
oniroute mission orchestrate "Refactor authentication middleware"
```

Formatted table output shows all 5 prepared components and recorded audit evidence.

---

## Parameter Flags

- `--workspace` / `-w`: Explicit workspace path override.
- `--json`: Output raw JSON representation.
- `--help` / `-h`: Display help options.
