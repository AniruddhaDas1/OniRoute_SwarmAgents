# OniRoute Knowledge Sources

## Purpose

A Knowledge Source is a canonical external origin from which Skills, Templates, Prompts, Documentation, or future assets may be discovered. A Source is provenance and discovery metadata; it is not a Skill, Package, Workflow, or Agent.

## Distinctions

- **Knowledge Source** — origin, trust, ownership, revision, and discovery boundary.
- **Skill** — bounded reusable capability conforming to the Skill Specification.
- **Package** — distributable layout containing a Skill and its declared metadata.
- **Workflow** — future coordination and sequencing contract.
- **Agent** — organizational responsibility and decision boundary.

A Source may expose candidate assets, but discovery does not imply import, normalization, admission, installation, or execution.

## Architecture

- [`sources/README.md`](sources/README.md) — Source catalog boundary.
- [`sources/SOURCE_SPECIFICATION.md`](sources/SOURCE_SPECIFICATION.md) — canonical Source metadata.
- [`sources/SOURCE_TYPES.md`](sources/SOURCE_TYPES.md) — supported origin types.
- [`sources/SOURCE_LIFECYCLE.md`](sources/SOURCE_LIFECYCLE.md) — lifecycle states.
- [`sources/TRUST_MODEL.md`](sources/TRUST_MODEL.md) — trust levels.
- [`sources/PROVENANCE_MODEL.md`](sources/PROVENANCE_MODEL.md) — source history.
- [`sources/DISCOVERY_MODEL.md`](sources/DISCOVERY_MODEL.md) — discovery and refresh behavior.

No connectors, source content, importers, or runtime behavior are introduced by this architecture.
