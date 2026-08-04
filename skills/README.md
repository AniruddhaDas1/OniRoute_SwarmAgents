# OniRoute Skills

The `skills/` layer defines reusable capability metadata, package conventions, and registry architecture. It does not contain executable skills in this phase.

## Relationship to the Specification

The [universal Skill Specification](specification/README.md) defines required metadata, contracts, lifecycle, versioning, provenance, licensing, and validation. Every package and registry record must conform to it.

## Relationship to Agents

Agents own organizational responsibilities. Skills provide bounded reusable capabilities that may be declared compatible with Agents or sub-agents; they do not change reporting or ownership.

## Relationship to Workflows

Workflows coordinate sequencing and handoffs. Skills are capability units that a future Workflow may reference; this architecture does not define execution.

## Relationship to Importers

Future importers may inspect GitHub, Git, ZIP, local, MCP, OCI, or remote registry sources. Imported artifacts must pass provenance, license, schema, contract, dependency, and compatibility validation before registry admission.

## Architecture

- [`specification/`](specification/README.md) — universal Skill metadata and governance.
- [`registry/`](registry/README.md) — storage, indexing, discovery, and lifecycle design.
- [`PACKAGING.md`](PACKAGING.md) — standard package layout.
- [`DISCOVERY.md`](DISCOVERY.md) — discovery classes and provenance.
- [`INDEXING.md`](INDEXING.md) — registry index fields and update model.
- [`SEARCH.md`](SEARCH.md) — declarative search strategy.
- [`REGISTRY_LIFECYCLE.md`](REGISTRY_LIFECYCLE.md) — registry state transitions.

No actual skill, package, importer, runtime, or search implementation is included.
