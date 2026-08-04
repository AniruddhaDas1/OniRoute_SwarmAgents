# OniRoute Skill Registry

## Purpose

The Registry is the catalog boundary for storing metadata, package references, validation evidence, versions, provenance, compatibility, and installation state for Skills. It indexes Skills; it does not execute them.

## Registry Metadata

Each record supports a unique Skill ID, version history, category, tags, license, author, organization, source, quality score, validation state, dependencies, compatibility, provider references, and installation status.

## Relationship to Skills

The Registry references packages that conform to the universal Skill Specification. Package content remains separate from registry metadata and is never inferred from a search index.

## Relationship to Agents

Compatibility fields identify Agents and sub-agents that may consume a Skill. Registry membership does not grant ownership, reporting authority, or permission to modify an Agent.

## Relationship to Workflows

Future Workflows may discover compatible Skills through the Registry. Sequencing and execution remain outside this architecture.

## Relationship to Future Importers

Future importers may submit source and provenance records for validation. Importers do not bypass licensing, dependency, compatibility, or quality gates.

## Registry Boundaries

This phase defines a registry architecture only. It does not implement storage, search, installation, runtime loading, distribution, or network access.

## Related Documents

- [`registry.schema.yaml`](registry.schema.yaml) — registry record metadata.
- [`../PACKAGING.md`](../PACKAGING.md) — package format.
- [`../DISCOVERY.md`](../DISCOVERY.md) — discovery model.
- [`../INDEXING.md`](../INDEXING.md) — indexing model.
- [`../SEARCH.md`](../SEARCH.md) — search strategy.
- [`../REGISTRY_LIFECYCLE.md`](../REGISTRY_LIFECYCLE.md) — registry states.
