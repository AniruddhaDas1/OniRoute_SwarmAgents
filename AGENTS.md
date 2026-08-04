# AGENTS.md

These instructions apply to future Codex sessions contributing to this repository.

## Project intent

Organization Level Swarm Coding AI Agents is an architecture-first framework. Preserve clear boundaries between organizational design, agent definitions, configuration, and the Runtime execution engine.

## Contribution rules

- Build in explicit phases; keep each change small and logically scoped.
- Keep Agent definitions declarative; skills, workflows, and prompts are resolved dynamically by Runtime v0.6.
- Prefer production-quality documentation and explain architectural decisions in `docs/`.
- Keep modules provider-independent and avoid embedding project-specific behavior in reusable agents.
- Every agent directory must contain a professional `README.md` and an `agent.yaml`.
- Give each agent one primary responsibility and document its inputs, outputs, and boundaries.
- Preserve backwards compatibility where practical; call out breaking changes clearly.
- Validate documentation, paths, and configuration before committing.
- Make small logical commits. Use descriptive conventional commit messages.

## Working sequence

1. Inspect the existing structure and relevant documentation.
2. State the intended scope and affected layer.
3. Implement the smallest coherent change.
4. Review for modularity, provider independence, and accidental scope expansion.
5. Run appropriate checks and summarize the result in the commit.
