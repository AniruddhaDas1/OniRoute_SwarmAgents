# Intelligent Context Optimization Engine

ICOE v1.1 is the provider-independent optimization layer between OniRoute Context and UMAL. It provides native optimization, governed context pruning, and an optional plugin architecture to prepare smaller, more relevant, traceable context before model invocation.

```text
Workflow → Execution → Context Engine → ICOE v1.1 → UMAL → Invocation → Model
```

The native pipeline covers Context, Prompt, Repository, Skill, Artifact, Terminal, and Conversation optimization under strict governance policy. Transformations preserve protected content, emit measurements and explainable reports, and fall back to native behavior when optional integrations are unavailable. Research references informed concepts only; no code or repository content was copied or imported.

## Native pipeline

`OptimizationRequest` produces an inspectable plan, optimized envelope, measurements, and report. Context optimization removes duplicate and empty entries and applies a byte budget while preserving protected keys. The focused optimizers normalize prompts, deduplicate Skills, reduce Markdown and JSON artifacts, retrieve Python symbols with the standard library AST, summarize terminal output, and prune repeated conversation messages.

## Plugins and optional integrations

The in-memory plugin registry declares capabilities, version, permissions, trust, health, compatibility, and optionality. The native plugin is always available. Optional integrations follow provider-neutral plugin contracts with governed safety policies.

## Benchmarks

Benchmarks record before/after bytes, estimated tokens, latency overhead, memory metadata, and reduction ratios. Token counts are deterministic estimates based on serialized representation and are not provider billing measurements.

## CLI

Use `oniroute optimize context`, `prompt`, `repository`, `artifact`, `terminal`, `conversation`, or `benchmark`. Inputs are explicit JSON/text values or a repository query; commands operate under policy-governed controls.

## Documents

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — boundaries and layer interactions.
- [`PIPELINE.md`](PIPELINE.md) — canonical optimization sequence.
- [`PLUGIN_MODEL.md`](PLUGIN_MODEL.md) — provider-neutral plugin contracts.
- [`OPTIMIZATION_TYPES.md`](OPTIMIZATION_TYPES.md) — module taxonomy.
- [`OPTIMIZATION_POLICIES.md`](OPTIMIZATION_POLICIES.md) — safety and quality policy.
- [`BENCHMARK_PLAN.md`](BENCHMARK_PLAN.md) — benchmark plan and validation methodology for ICOE v1.1.
- [`RESEARCH_NOTES.md`](RESEARCH_NOTES.md) — external reference findings and provenance.
