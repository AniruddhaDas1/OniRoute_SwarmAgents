# Organization Level Swarm Coding AI Agents

Organization Level Swarm Coding AI Agents is an architecture-first framework for coordinating specialized AI coding agents as an engineering organization.

The project starts with a durable repository foundation. It defines where organizational knowledge, agents, and configuration will live before adding execution mechanisms. The result should be understandable to people, adaptable to different model providers, and safe to evolve over time.

## Vision

Software development is a system of collaborating responsibilities, not a single undifferentiated task. This project models that system explicitly: a coordinating layer delegates to focused agents, each agent owns a bounded area of concern, and decisions remain inspectable in the repository.

The long-term vision is a reusable, provider-independent operating model for AI-assisted engineering teams that can be applied across many products and technology stacks.

## Goals

- Establish a clear organization and ownership model for coding agents.
- Keep each agent focused, composable, and independently maintainable.
- Separate reusable framework architecture from project-specific implementation.
- Make decisions, boundaries, and configuration discoverable in version control.
- Support multiple model providers and execution environments without architectural lock-in.
- Grow incrementally, with documentation and validation preceding automation.

## Architecture philosophy

The repository is intentionally layered:

```text
Human / Product Context
          |
     Coordinating Layer
          |
   Organizational Agents
          |
  Domain and Platform Agents
          |
     Project Execution
```

Agents should have one primary responsibility, explicit interfaces, and minimal assumptions about other agents. Coordination belongs at the organizational layer; domain expertise belongs in agents; deployment-specific choices belong in configuration. This separation keeps the system testable and permits components to be replaced without redesigning the whole framework.

The current architecture defines Executive, Engineering, and Platform agents as documentation and configuration only. Sub-agents, skills, workflows, adapters, MCP integrations, and runtime execution remain deferred until their boundaries are stable.

## Repository layout

- [`agents/`](agents/README.md) — definitions and conventions for the Executive, Engineering, and Platform layers.
- [`config/`](config/README.md) — configuration boundaries and environment-specific settings.
- [`docs/`](docs/README.md) — architecture decisions, specifications, and project guidance.
- [`AGENTS.md`](AGENTS.md) — instructions for future Codex sessions contributing to this repository.

## Roadmap

1. **Foundation** — establish repository conventions and documentation.
2. **Organization model** — define executive, engineering, and platform layers.
3. **Agent catalog** — introduce focused organizational and domain agents.
4. **Composition** — define delegation, context exchange, and observability contracts.
5. **Execution** — add skills and workflows only after their boundaries are documented and reviewed.
6. **Knowledge and integrations** — add context, knowledge, and MCP integrations as replaceable adapters.

The roadmap is directional. Each phase should produce a usable, documented increment and preserve provider independence.

## Status

This repository has defined and frozen its Executive, Engineering, and Platform organization layers. No executable agent runtime is promised yet.

## License

Released under the MIT License. See [`LICENSE`](LICENSE).
