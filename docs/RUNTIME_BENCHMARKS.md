# Runtime Benchmarks

Measurements were recorded on 2026-08-04 using Python 3.14.6 on the local development machine. They are observational baselines.

| Operation | Measurement |
|---|---:|
| Cold repository load and registry build | 5,437.925 ms |
| NetworkX graph build | 84.598 ms |
| Workflow Context creation | 84.184 ms |
| Workflow plan creation | 208.824 ms |
| Peak traced memory during representative pipeline | 28,623,409 bytes |
| Full 28-test suite | 27.20 s |

The loaded registry contains 31 top-level Agents, 265 Sub-Agents, 1,087 Skills, 20 Workflows, one Knowledge Source record, one Package record, five Mapping records, and two registry records. Invocation translation was validated against an in-process HTTP mock; external network latency was intentionally excluded.
