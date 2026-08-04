# Contributing to OniRoute

Thank you for your interest in contributing to OniRoute Swarm Agents. This document describes how to contribute within the frozen v1.0.0 architecture.

## Before you begin

- Review the [README](https://github.com/AniruddhaDas1/OniRoute_SwarmAgents#oniroute-swarm-agents) and [Architecture Overview](ARCHITECTURE_OVERVIEW.md).
- Run `oniroute doctor` to confirm the repository validates locally before making changes.
- Open an issue to discuss any significant architectural or behavioral change before starting work. Significant changes that touch frozen layers require an approved Architecture Change Request (ACR); see [Architecture History](ARCHITECTURE_HISTORY.md) and [Versioning](VERSIONING.md).

## Scope

OniRoute v1.0.0 is architecture-complete. Runtime v0.6, Motion Engineering, and ICOE v1.1 are frozen. Contributions are welcome within these boundaries:

- Documentation improvements and corrections.
- Non-frozen configuration, mapping, or metadata extensions that do not alter frozen contracts.
- Bug fixes in runtime behavior that preserve frozen interfaces.
- New tests that increase coverage without changing architecture.

The following are frozen and require an approved ACR or authorized release phase before changes:

- Agents, Sub-Agents, and agent directory structure.
- Official Skills and skill metadata schemas.
- Workflows, Workflow schemas, and the Official Workflow library.
- Knowledge Source schemas and registry records.
- Schemas, CLI interfaces, and runtime behavior (v0.6).
- Motion Engineering artifacts and Motion Skills.
- Community metadata ingestion and import policies.
- Configuration and governance contracts.

## Process

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/my-change`.
3. Make your change, keeping it small and logically scoped.
4. Add or update tests and documentation as needed.
5. Run the full validation suite:

   ```bash
   python -m pytest -q
   oniroute doctor
   git diff --check
   ```

6. Commit using conventional commits:

   ```bash
   git commit -F - <<'EOF'
   docs: improve README navigation consistency
   EOF
   ```

7. Open a pull request using the [pull-request template](../.github/PULL_REQUEST_TEMPLATE.md). Clearly state the affected layer, compatibility impact, and validation result.

## Guidelines

- Prefer production-quality documentation. Architectural decisions belong in `docs/`.
- Keep modules provider-independent. Do not embed provider-specific behavior in reusable agents, Skills, or Workflows.
- Preserve backwards compatibility where practical; call out breaking changes clearly.
- Never commit secrets, credentials, generated environments, or provider-specific coupling.
- Follow the [Code of Conduct](../.github/CODE_OF_CONDUCT.md).

See the [Developer Guide](DEVELOPER_GUIDE.md) for technical conventions (Pydantic contracts, PyYAML metadata, NetworkX relationships, Typer/Rich CLI, standard-library HTTP at adapter boundaries).
