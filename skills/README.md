# OniRoute Skills

The `skills/` layer defines reusable capability metadata, Official Skills, package conventions, and registry architecture.

## Relationship to Agents

Agents own organizational responsibilities. Skills provide bounded, reusable capabilities. Skills are resolved externally by Runtime v0.6 through the External Mapping Registry and are intentionally not embedded inside Agent YAML.

## Relationship to Workflows

Workflows coordinate sequencing and handoffs. Official Skills are resolved dynamically at step execution by Runtime v0.6.

## Relationship to Importers

Community Skill entries provide declarative metadata for discovery, import, and provenance validation. Importers inspect GitHub, Git, ZIP, local, MCP, OCI, or remote registry sources. Imported artifacts must pass provenance, license, schema, contract, dependency, and compatibility validation before registry admission.

## Architecture

- [`specification/`](specification/README.md) — universal Skill metadata and governance.
- [`official/`](official/README.md) — Official versioned Skill Library.
- [`registry/`](registry/README.md) — storage, indexing, discovery, and lifecycle design.
- [`PACKAGING.md`](PACKAGING.md) — standard package layout.
- [`DISCOVERY.md`](DISCOVERY.md) — discovery classes and provenance.
- [`INDEXING.md`](INDEXING.md) — registry index fields and update model.
- [`SEARCH.md`](SEARCH.md) — declarative search strategy.
- [`REGISTRY_LIFECYCLE.md`](REGISTRY_LIFECYCLE.md) — registry state transitions.
