# OniRoute Workflow Composition and Resolution

This directory defines how Workflow contracts relate, are selected, composed, and resolved as metadata. It is provider-independent, runtime-independent, implementation-independent, and declarative.

It defines no Workflow instances, execution engine, runtime, CLI, prompt, adapter, package, or Agent/Skill changes.

## Documents

- [`WORKFLOW_RESOLUTION.md`](WORKFLOW_RESOLUTION.md) — canonical resolution order.
- [`WORKFLOW_COMPOSITION.md`](WORKFLOW_COMPOSITION.md) — composition forms and boundaries.
- [`WORKFLOW_SELECTION.md`](WORKFLOW_SELECTION.md) — request and registry selection criteria.
- [`WORKFLOW_DEPENDENCIES.md`](WORKFLOW_DEPENDENCIES.md) — declarative dependency integrity.
- [`WORKFLOW_BRANCHING.md`](WORKFLOW_BRANCHING.md) — logical transition types.
- [`WORKFLOW_CONTEXT_FLOW.md`](WORKFLOW_CONTEXT_FLOW.md) — context movement and provenance.
- [`WORKFLOW_APPROVAL_FLOW.md`](WORKFLOW_APPROVAL_FLOW.md) — approval declarations.
- [`WORKFLOW_FALLBACK.md`](WORKFLOW_FALLBACK.md) — policy-preserving fallback handling.
- [`WORKFLOW_CONFLICTS.md`](WORKFLOW_CONFLICTS.md) — metadata-only conflict resolution.
- [`WORKFLOW_REUSE.md`](WORKFLOW_REUSE.md) — reusable contract blocks.

## Validation

A resolved description is valid only when composition, dependency, branch, approval, context, conflict, and reuse integrity checks pass and the canonical resolution order produces a consistent result. Validation evaluates declarations and references only; it does not test or simulate execution.
