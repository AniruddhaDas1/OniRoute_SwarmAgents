# CLI Reference

| Command | Purpose |
|---|---|
| `doctor` | Load and validate the repository |
| `list agents|skills|workflows` | List metadata |
| `inspect agent|skill|workflow|context|model|provider|tool|mcp` | Inspect one record |
| `search QUERY` | Search metadata |
| `context workflow|agent|skill ID` | Build Context views |
| `plan workflow ID` / `run workflow ID` | Plan or run locally |
| `history`, `events`, `trace` | Inspect process-local execution data |
| `explain workflow ID`, `explain execution` | Explain resolution and execution |
| `models`, `providers`, `capabilities`, `recommend-model` | Model catalog and selection |
| `tools`, `mcp`, `recommend-tool` | Tool/MCP metadata and selection |
| `invoke` | Invoke through UMAL and a configured adapter |
| `policy`, `audit`, `permissions`, `approvals`, `budget` | Governance views |

Use `oniroute COMMAND --help` for options. Unknown identifiers and policy failures return non-zero exit codes.
