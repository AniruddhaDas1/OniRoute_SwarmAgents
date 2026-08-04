# Runtime Limitations

- Repository loading is metadata-volume bound and currently takes about 5.4 seconds cold.
- History, events, budgets, audits, Context storage, and generated artifacts are process-local and non-persistent.
- Most Workflow participant names are semantic roles rather than normalized registry IDs.
- Streaming adapters currently expose a unified iterator but reference adapters return one completed chunk.
- Retry, fallback, timeout, and circuit-breaker policy vocabulary is broader than the currently implemented bounded retry behavior.
- Tool records and MCP servers are metadata only; no Tool or MCP execution exists.
- OpenAI-compatible and Ollama are the only implemented invocation translations. Other protocols remain interfaces.
- Real endpoint availability, authentication, cost, and model quality are environment responsibilities.
- Governance is local configuration, not enterprise IAM or a remote policy authority.

Future extensions require a new approved phase and must preserve frozen v0.6 choke points and provider independence.
