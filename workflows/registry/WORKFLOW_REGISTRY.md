# Workflow Registry Architecture

The Workflow Registry is a provider- and runtime-independent metadata catalog. A registry record identifies a Workflow, summarizes compatibility and governance state, and points to authoritative source and provenance information.

## Registry contract

The registry supports discovery, indexing, metadata, cataloging, admission, compatibility, provenance, and lifecycle governance. Registry membership means that a record passed its declared admission level; it does not authorize use, imply execution readiness, or modify the Workflow contract.

Registry records must remain traceable to the canonical Workflow metadata defined in [`../specification/WORKFLOW_SCHEMA.yaml`](../specification/WORKFLOW_SCHEMA.yaml). Registry-specific fields such as classification, trust level, admission evidence, registry version, and history supplement rather than replace that contract.

## Boundaries

The registry does not create Workflow instances, sequence Agents, invoke Skills, resolve dependencies, produce artifacts, enforce approvals, or implement search and indexing. Storage, APIs, runtimes, engines, prompts, providers, and deployment choices remain outside this architecture.
