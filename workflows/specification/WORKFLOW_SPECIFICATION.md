# Workflow Specification

A Workflow is a reusable, declarative contract for collaboration among Agents to achieve an engineering outcome. It defines participants, boundaries, information exchange, gates, artifacts, and completion criteria.

## Non-goals

Workflows are not prompts, code, instances, plans for a particular product, execution graphs, runtimes, engines, CLIs, adapters, packages, or provider integrations. A schema declaration does not authorize execution.

## Design principles

Workflows are provider-, runtime-, and implementation-independent; composable; inspectable; versioned; auditable; and explicit about ownership, context, decisions, approvals, dependencies, and failure handling.

The canonical metadata shape is [`WORKFLOW_SCHEMA.yaml`](WORKFLOW_SCHEMA.yaml). Supporting documents define the meaning and validation of each part.
