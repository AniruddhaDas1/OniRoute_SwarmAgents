# FAQ

## Does OniRoute require cloud AI?

No. Metadata, validation, planning, governance, and Dry Run are local. Ollama and OpenAI-compatible local servers are supported through configuration.

## Does every listed provider have an adapter?

No. Provider entries are metadata. OpenAI-compatible and Ollama are the reference invocation implementations.

## Are Tools and MCP servers executed?

No. v0.6 discovers, selects, and governs Tool/MCP metadata only.

## Is state persisted?

No. Context, history, events, budgets, audits, and artifacts are process-local.
