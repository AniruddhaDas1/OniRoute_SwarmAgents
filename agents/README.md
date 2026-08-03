# Agents

This directory will contain the framework's specialized agent definitions.

An agent is a bounded organizational capability, not a general-purpose assistant. Each future agent must include:

- `README.md` describing its responsibility, boundaries, inputs, outputs, and dependencies.
- `agent.yaml` containing its machine-readable identity and configuration.

Agent definitions should remain reusable across projects and model providers. Coordination contracts belong in shared documentation; implementation-specific settings belong in `config/`.

No executable agents are included in the foundation phase.
