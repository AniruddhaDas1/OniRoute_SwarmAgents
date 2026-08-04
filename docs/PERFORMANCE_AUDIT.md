# Performance Audit

Measurements were collected on the audit host using median wall-clock time after local installation. They are development-host observations, not service-level guarantees.

| Operation | Median |
|---|---:|
| Repository load and registry build | 1,857.331 ms |
| Resolution graph construction | 13.024 ms |
| Workflow Context creation | 13.238 ms |
| Native Context optimization | 0.008 ms |
| Workflow planning | 28.196 ms |
| Dry-run deterministic execution | 0.102 ms |
| CLI startup/help | 187.330 ms |
| Repository load peak traced memory | 27.277 MiB |

The canonical ICOE fixture reduced representation size from 54 to 20 bytes and estimated tokens from 13 to 5. Results are consistent with earlier reports: metadata loading dominates local latency; graph, Context, planning, optimization, and deterministic execution remain small by comparison. No premature optimization is recommended.
