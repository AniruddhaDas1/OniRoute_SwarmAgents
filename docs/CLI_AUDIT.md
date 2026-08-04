# CLI Audit

Top-level help and command help returned exit code 0 for: doctor, list, inspect, search, plan, run, trace, explain, invoke, models, providers, capabilities, tools, mcp, recommend-model, recommend-tool, policy, audit, permissions, approvals, budget, and optimize.

Repository-backed `doctor` passed. Optimization explain and benchmark commands passed. Commands requiring identifiers correctly expose required arguments; invocation was not sent to a live endpoint during the audit. Rich formatting is consistent with the existing compact CLI style. Command names match `docs/CLI_REFERENCE.md` and optimization documentation.

Known constraint: history, events, audit, and optimization report commands describe the current process only; separate CLI processes do not share in-memory records.
