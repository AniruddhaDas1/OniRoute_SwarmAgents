# Runtime Performance Benchmarks (ACR-006 Phase R5)

**Environment:** macOS (Apple Silicon), Python 3.14  
**Date:** 2026-08-05  

---

## 1. Overview & Baseline Purpose

This document provides the empirical baseline performance metrics for the **OniRoute Agent Runtime (v0.6.0)**. These benchmarks serve as an unyielding reference line for future releases (such as ACR-007 Multi-Agent Collaboration).

---

## 2. Empirical Benchmark Metrics

The baseline metrics were measured using [`scripts/benchmark_runtime.py`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/scripts/benchmark_runtime.py):

| Metric | Measured Baseline | Throughput | Description |
|---|:---:|:---:|---|
| **Session Initialization** | **0.116 ms** / op | **8,649.4 ops/sec** | Time to create and initialize sessions from an `ExecutionBlueprint` |
| **Recovery Pause/Resume** | **0.0417 ms** / op | **23,980 ops/sec** | Overhead of pausing a session to `WAITING` and resuming to `RUNNING` |
| **Recovery Retry Attempt** | **0.0383 ms** / op | **26,109 ops/sec** | Overhead of classifying failure, computing backoff, and logging `RetryRecord` |
| **Artifact Collection** | **0.0018 ms** / art | **548,671.6 art/sec** | In-memory artifact registration and lineage recording |
| **Peak Memory Footprint** | **44.78 MB** | N/A | Total traced memory during full blueprint initialization, execution, and report generation |

---

## 3. Component Latency Profile

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Agent Session Lifecycle Latency Breakdown                                    │
└─────────────────────────────────────────────────────────────────────────────┘
  Session Init   [░░░░░░░░░░░]  0.116 ms
  Pause / Resume [░░░░]         0.042 ms
  Retry Record   [░░░]          0.038 ms
  Artifact Reg   [░]            0.002 ms
```

---

## 4. Scalability Boundaries

1. **In-Memory Scale:** Supports initialization of > 8,000 sessions/second on a single CPU core.
2. **Artifact Collector:** In-memory registration handles > 500,000 artifacts/second with zero I/O bottleneck.
3. **Memory Baseline:** Under 45 MB peak memory footprint for typical multi-member organization blueprints.
