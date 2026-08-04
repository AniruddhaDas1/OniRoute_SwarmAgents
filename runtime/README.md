# OniRoute Local Runtime Foundation

The runtime discovers and parses repository metadata, builds in-memory indexes, validates integrity, and exposes read-only lookup APIs. It operates entirely from a cloned repository without a server, database, cloud service, telemetry, tracking, or network dependency.

## Architecture

- `loader.py` discovers Agent, Skill, Workflow, Knowledge, Package, Mapping, and registry YAML.
- `registry.py` builds non-persistent indexes and records duplicates.
- `validator.py` checks canonical Workflow metadata, registry references, duplicates, and Workflow dependency cycles.
- `resolver.py` provides read-only identity, tag, and category lookup.
- `resolver.py` resolves Agent, Skill, Workflow, Knowledge Source, Package, and relationship metadata and builds a read-only NetworkX graph.
- `models.py` contains tolerant Pydantic models for frozen heterogeneous metadata.
- `cli/main.py` provides `oniroute doctor`, list, inspect, and metadata search commands.

## Resolution Engine

Resolution answers repository questions by ID, category, tag, owner, participant, artifact, and declared relationship. It does not traverse a Workflow for execution, schedule work, invoke Skills, or call a provider.

## Graph model

The in-memory graph uses typed metadata nodes and labeled directed edges for parent/child, ownership, compatibility, dependency, artifact, participant, and package relationships. It is rebuilt on load and never persisted.

## CLI commands

- `oniroute list agents|skills|workflows`
- `oniroute inspect agent|skill|workflow <id>`
- `oniroute search <query>`
- `oniroute doctor`

## Boundaries

This foundation does not execute Agents, Skills, or Workflows. It has no LLM providers, orchestration, context engine, task execution, MCP, plugins, adapters, API keys, persistence, or remote access. Future phases may extend validation and resolution without weakening these boundaries.
