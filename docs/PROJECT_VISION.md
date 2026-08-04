# Project Vision

OniRoute_SwarmAgents is an architecture-first framework for modeling and operating a governed engineering organization composed of specialized Agents, reusable Skills, declarative Workflows, Knowledge Sources, model abstractions, Tools, and a local Python runtime.

## Design philosophy

- Architecture first: ownership, boundaries, provenance, policy, and information flow are explicit repository contracts before execution.
- Provider independence: core contracts do not depend on a specific model vendor, cloud, SDK, or hosted service.
- Model independence: model selection is capability-driven through the Universal Model Abstraction Layer (UMAL).
- Governance first: policy, approvals, permissions, risk, budgets, and audit are execution boundaries.
- Local first: discovery, validation, planning, Dry Run, optimization, and metadata operations work locally.
- Community metadata only: Community repositories are represented through independently authored metadata without redistributing upstream content.

## Target users

AI platform engineers, software architects, agent-system researchers, developer-tool builders, and teams that need a provider-independent foundation instead of an application tied to one model API.

## Current status

Version 1.0.0 is architecture-complete. Runtime v0.6, Motion Engineering, and the Intelligent Context Optimization Engine (ICOE) v1.1 are frozen. Future architectural changes require an approved Architecture Change Request (ACR). See [Architecture History](ARCHITECTURE_HISTORY.md) for the full evolution.
