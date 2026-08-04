# ICOE Benchmark Plan

Phase O2 should build fixtures and measurement tooling before algorithms. The benchmark compares original Context, individual modules, plugin combinations, and fallback behavior.

## Metrics

- Bytes and estimated/provider-token counts before and after.
- Retained required facts, protected-content retention, citation/provenance completeness, and structured-contract validity.
- Task outcome or answer-quality delta using provider-independent rubrics and multiple model classes.
- Retrieval precision/recall for symbols, dependencies, and artifacts.
- False omission, false duplication, stale-index, and hallucinated-structure rates.
- Planning/optimization latency, peak memory, cacheability, and plugin failure rate.
- Terminal diagnostic fidelity: failure, warning, path, line, and exit-code retention.
- Cost-performance frontier rather than token reduction alone.

## Corpora and scenarios

Use frozen OniRoute metadata, small/medium/large open-source repositories with licensing clearance, long conversations, repeated Context, JSON/Markdown artifacts, test/build logs, and adversarial protected-content cases. Pin commits and fixture versions.

## Acceptance gates

No protected-content loss; deterministic replay; provenance completeness; safe behavior on malformed input; measurable reduction without unacceptable quality loss; and no regression against original Context on critical tasks. Report per-module results—never generalize one corpus or model result to all workloads.
