# OniRoute Workflow Registry

The Workflow Registry is the canonical catalog boundary for discovering, classifying, admitting, indexing, and governing Workflow metadata. It references Workflows conforming to the universal Workflow specification; it does not contain Workflow instances or execute orchestration.

## Responsibilities

- Preserve canonical registry metadata and immutable provenance.
- Support metadata-based discovery, cataloging, search, and indexing.
- Record admission evidence, compatibility, trust, quality, and lifecycle.
- Keep Workflow definitions, runtime systems, providers, and storage implementations outside the registry architecture.

## Documents

- [`WORKFLOW_REGISTRY.md`](WORKFLOW_REGISTRY.md) — registry responsibilities and boundaries.
- [`WORKFLOW_REGISTRY_SCHEMA.yaml`](WORKFLOW_REGISTRY_SCHEMA.yaml) — canonical registry record schema.
- [`WORKFLOW_DISCOVERY.md`](WORKFLOW_DISCOVERY.md) — discovery dimensions.
- [`WORKFLOW_CATALOG.md`](WORKFLOW_CATALOG.md) — catalog organization.
- [`WORKFLOW_SEARCH.md`](WORKFLOW_SEARCH.md) — metadata search contract.
- [`WORKFLOW_INDEXING.md`](WORKFLOW_INDEXING.md) — indexing strategy.
- [`WORKFLOW_ADMISSION.md`](WORKFLOW_ADMISSION.md) — admission gates.
- [`WORKFLOW_CLASSIFICATION.md`](WORKFLOW_CLASSIFICATION.md) — classifications and categories.
- [`WORKFLOW_TAGGING.md`](WORKFLOW_TAGGING.md) — tag governance.
- [`WORKFLOW_PROVENANCE.md`](WORKFLOW_PROVENANCE.md) — immutable origin and history.

The registry defines no storage service, search implementation, CLI, prompt, adapter, package, execution engine, or provider integration.
