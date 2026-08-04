# Agents

This directory contains the framework's frozen Executive, Engineering, and Platform agent definitions.

An agent is a bounded organizational capability, not a general-purpose assistant. Each agent definition must include:

- `README.md` describing its responsibility, boundaries, inputs, outputs, and dependencies.
- `agent.yaml` containing its machine-readable identity and configuration.
- `SYSTEM.md` containing concise, provider-independent operating instructions.

Agent definitions should remain reusable across projects and model providers. Coordination contracts belong in shared documentation; implementation-specific settings belong in `config/`.

The current definitions are non-executable. Sub-agents, skills, workflows, adapters, MCP integrations, and runtime behavior remain deferred.
