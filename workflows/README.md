# OniRoute Workflow Specification

Workflows are first-class, declarative orchestration contracts describing how bounded Agents collaborate toward an engineering outcome. Workflow metadata remains declarative, while workflow planning and execution are performed by Runtime v0.6.

## Scope

This directory defines provider-independent metadata, contracts, lifecycle, context, artifact, dependency, decision, failure, security, approval, official workflows, and validation rules. Workflow execution, state transitions, and step invocation are orchestrated by Runtime v0.6.

## Documents

- [`specification/WORKFLOW_SPECIFICATION.md`](specification/WORKFLOW_SPECIFICATION.md) — architecture and boundaries.
- [`specification/WORKFLOW_SCHEMA.yaml`](specification/WORKFLOW_SCHEMA.yaml) — canonical metadata schema.
- [`specification/WORKFLOW_CONTRACT.md`](specification/WORKFLOW_CONTRACT.md) — contract sections.
- [`specification/WORKFLOW_LIFECYCLE.md`](specification/WORKFLOW_LIFECYCLE.md) — lifecycle states.
- [`specification/WORKFLOW_VERSIONING.md`](specification/WORKFLOW_VERSIONING.md) — compatibility and revisions.
- [`specification/WORKFLOW_DEPENDENCIES.md`](specification/WORKFLOW_DEPENDENCIES.md) — declarative dependencies.
- [`specification/WORKFLOW_VALIDATION.md`](specification/WORKFLOW_VALIDATION.md) — validation rules.
- [`specification/WORKFLOW_CONTEXT.md`](specification/WORKFLOW_CONTEXT.md) — context boundaries and provenance.
- [`specification/WORKFLOW_ARTIFACTS.md`](specification/WORKFLOW_ARTIFACTS.md) — metadata-only artifact model.
- [`specification/WORKFLOW_DECISIONS.md`](specification/WORKFLOW_DECISIONS.md) — decision model.
- [`specification/WORKFLOW_FAILURES.md`](specification/WORKFLOW_FAILURES.md) — failure states and recovery declarations.
- [`specification/WORKFLOW_SECURITY.md`](specification/WORKFLOW_SECURITY.md) — security classification.
- [`specification/WORKFLOW_APPROVALS.md`](specification/WORKFLOW_APPROVALS.md) — approval gates.
- [`registry/README.md`](registry/README.md) — registry discovery, catalog, admission, indexing, and provenance architecture.
- [`resolution/README.md`](resolution/README.md) — declarative Workflow composition, selection, resolution, branching, fallback, and reuse architecture.
- [`official/`](official/) — the versioned Official Workflow Library.
- [`governance/README.md`](governance/README.md) — Workflow governance and freeze policies.
- [`validation/README.md`](validation/README.md) — v0.5 validation evidence and matrices.
