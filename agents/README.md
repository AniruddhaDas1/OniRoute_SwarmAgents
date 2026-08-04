# Agents

This directory contains the framework's frozen Executive, Engineering, and Platform agent definitions.

An agent is a bounded organizational capability, not a general-purpose assistant. Each agent definition must include:

- `README.md` describing its responsibility, boundaries, inputs, outputs, and dependencies.
- `agent.yaml` containing its machine-readable identity and configuration.
- `SYSTEM.md` containing concise, provider-independent operating instructions.

Agent definitions should remain reusable across projects and model providers. Coordination contracts belong in shared documentation; implementation-specific settings belong in `config/`.

Agent definitions remain intentionally declarative. Empty configuration arrays in `agent.yaml` (such as `skills: []`, `workflows: []`, or `adapters: []`) represent strict architectural boundaries, not missing functionality.

Agent capabilities, context, tool access, and workflows are resolved dynamically at execution time by Runtime v0.6 through:
- **Runtime Resolution Engine**: Validates agent boundaries and loads declarative metadata.
- **External Mapping Registry & Registries**: Maps capabilities, skills, workflows, and knowledge dynamically.
- **Context Engine & ICOE v1.1**: Generates optimized token budgets and prompt contexts.
- **Universal Model Abstraction Layer (UMAL) & Invocation Layer**: Handles provider-agnostic model routing and protocol translation.
- **Governance & Policy Layer**: Controls tool execution, security policy, and step-level dry-run evaluation.
