# Runtime Validation Report

## Result

**PASS — OniRoute Runtime v0.6 integration validated.**

The 28-test suite covers repository loading, registries, YAML validation, duplicate and broken references, graph resolution, Context construction/filtering/routing/serialization, deterministic execution, artifacts, events, history, UMAL selection, Tool/MCP selection, OpenAI-compatible and Ollama adapters with a local mock server, AI Dry Run and Automatic mock execution, governance, permissions, approvals, budgets, security, auditing, and CLI behavior.

End-to-end scenarios passed for repository loading, Workflow planning/execution, AI Dry Run, mock AI execution, Tool recommendation, governance allow/deny, approval required, Context routing, history, audit records, artifacts, and CLI inspection. Failure tests cover missing/broken metadata, duplicate IDs, broken/circular Workflow references, unknown catalog records, missing adapters, permission/security denial, approval requirements, and budget exhaustion.

All four configuration files parse as YAML. `oniroute doctor` exits successfully with zero errors, warnings, or duplicates.
