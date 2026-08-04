# Intelligent Context Optimization Engine

ICOE is the proposed provider-independent optimization layer between OniRoute Context and UMAL. It prepares smaller, more relevant, traceable context without executing models, Tools, Workflows, or optimization algorithms in Phase O1.

```text
Workflow → Execution → Context Engine → ICOE → UMAL → Invocation → Model
```

The architecture covers Context, Prompt, Repository, Skill, Artifact, Terminal, and Conversation optimization. Every transformation is policy-bound, measurable, reversible where required, provenance-preserving, and optional. Research references informed concepts only; no code or repository content was copied or imported.

## Documents

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — boundaries and layer interactions.
- [`PIPELINE.md`](PIPELINE.md) — canonical optimization sequence.
- [`PLUGIN_MODEL.md`](PLUGIN_MODEL.md) — provider-neutral plugin contracts.
- [`OPTIMIZATION_TYPES.md`](OPTIMIZATION_TYPES.md) — module taxonomy.
- [`OPTIMIZATION_POLICIES.md`](OPTIMIZATION_POLICIES.md) — safety and quality policy.
- [`BENCHMARK_PLAN.md`](BENCHMARK_PLAN.md) — evidence plan for future implementation.
- [`RESEARCH_NOTES.md`](RESEARCH_NOTES.md) — external reference findings and provenance.
