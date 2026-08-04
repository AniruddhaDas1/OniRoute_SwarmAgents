# OniRoute Local Runtime Foundation

The runtime discovers and parses repository metadata, builds in-memory indexes, validates integrity, and exposes read-only lookup APIs. It operates entirely from a cloned repository without a server, database, cloud service, telemetry, tracking, or network dependency.

## Architecture

- `loader.py` discovers Agent, Skill, Workflow, Knowledge, Package, Mapping, and registry YAML.
- `registry.py` builds non-persistent indexes and records duplicates.
- `validator.py` checks canonical Workflow metadata, registry references, duplicates, and Workflow dependency cycles.
- `resolver.py` provides read-only identity, tag, and category lookup.
- `models.py` contains tolerant Pydantic models for frozen heterogeneous metadata.
- `cli/main.py` provides `oniroute doctor`.

## Boundaries

This foundation does not execute Agents, Skills, or Workflows. It has no LLM providers, orchestration, context engine, task execution, MCP, plugins, adapters, API keys, persistence, or remote access. Future phases may extend validation and resolution without weakening these boundaries.
