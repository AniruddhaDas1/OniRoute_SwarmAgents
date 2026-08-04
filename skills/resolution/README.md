# Agent–Skill Resolution Architecture

## Purpose

Resolution defines how an Agent request is translated into a compatible, governed set of Skills from the Registry. It is a decision architecture, not a runtime implementation.

## Relationship to the Registry

The Registry supplies searchable metadata, versions, validation evidence, lifecycle state, dependencies, compatibility, provenance, and installation status. Resolution may query and evaluate those records but does not mutate the Registry.

## Relationship to Agents

Agents remain immutable owners of responsibilities. Resolution uses declared Agent and sub-agent compatibility to select Skills; it never changes reporting, ownership, or Agent definitions.

## Relationship to Workflows

Future Workflows may request or compose Skills through a resolution result. Workflow sequencing and approval remain separate concerns.

## Relationship to Runtime

The future Runtime may consume an approved resolution result. This architecture defines no execution, tool invocation, package loading, or network behavior.

## Documents

- [`RESOLUTION_PIPELINE.md`](RESOLUTION_PIPELINE.md) — resolution lifecycle.
- [`SELECTION_POLICY.md`](SELECTION_POLICY.md) — admissibility factors.
- [`RANKING_MODEL.md`](RANKING_MODEL.md) — comparative ranking.
- [`COMPOSITION_MODEL.md`](COMPOSITION_MODEL.md) — atomic and composite selection.
- [`FALLBACK_POLICY.md`](FALLBACK_POLICY.md) — unavailable and ambiguous cases.
- [`CACHE_POLICY.md`](CACHE_POLICY.md) — resolution cache governance.
- [`RESOLUTION_CONTEXT.md`](RESOLUTION_CONTEXT.md) — context requirements and propagation.
