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

## Context lifecycle

`ContextBuilder` creates immutable Workflow, Agent, Skill, Artifact, Repository, and metadata-only Execution contexts. `ContextRouter` emits a routing plan from Workflow to Agent, Skill, Artifact, and next Agent without execution. `ContextFilter` applies allow/block lists, redaction, compression, priority, scope, and a non-AI summarization placeholder. `ContextSerializer` supports dictionaries, JSON, YAML, and Pydantic models. `InMemoryContextStorage` is process-local and non-persistent.

## Execution lifecycle

The local engine loads and resolves Workflow metadata, prepares context, creates a deterministic five-step plan, advances Pending → Running → Completed states, emits in-memory events, and produces six metadata artifacts. AI-associated steps return `Placeholder: AI execution not yet implemented` and continue. Plans use stable IDs and execution order; elapsed duration and event timestamps are observational only.

Events cover WorkflowStarted, StepStarted, StepCompleted, StepSkipped, ArtifactGenerated, WorkflowCompleted, and WorkflowFailed. History, events, and artifacts live only in the current process. CLI commands are `oniroute plan workflow <id>`, `oniroute run workflow <id>`, `oniroute history`, and `oniroute events`.

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
