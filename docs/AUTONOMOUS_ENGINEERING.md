# Phase P5 — Autonomous Engineering Architecture

## 1. Subsystem Overview

**Autonomous Engineering (Phase P5)** is the code execution and implementation generation stage of OniRoute v1.2.

```
EngineeringContractReport (P4.G4/P4.G5) ──► Engineering Worker Engine (P5.E1) ──► EngineeringResult ──► Cross-Agent Review (P5.E2)
```

Phase P5.E1 is the **FIRST phase permitted to**:
- Invoke LLMs and model providers via Unified Model Abstraction Layer (UMAL)
- Call Model Context Protocol (MCP) tools
- Create and modify source code, configuration, documentation, tests, and assets in target workspace
- Write implementation artifacts to storage

---

## 2. Core Safety Boundaries

1. **Strict Contract Scoping**: Engineering workers generate code **ONLY** for targets allocated in the input [`EngineeringContractReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/contracts/models.py#L35).
2. **Engine Root Read-Only Enforcement**: Any write attempt into engine root files raises an [`EngineeringBoundaryViolation`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/engineering/exceptions.py#L12).
3. **Workspace Path Sandboxing**: Paths attempting directory traversal outside workspace root are rejected.
4. **Immutable Output Result**: Generates frozen [`EngineeringResult`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/engineering/models.py#L9) per contract.
