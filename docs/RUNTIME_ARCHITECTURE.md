# OniRoute Runtime Architecture v0.6

OniRoute is a local, provider-independent Python runtime that loads frozen repository metadata and routes all AI and Tool requests through canonical abstractions and governance.

```text
CLI / Workflow Engine
        |
Resolution -> Context -> Execution Plan
        |                    |
        |              Governance Policy
        |                 /          \
       UMAL -> Invocation Layer    Tool Layer
                    |                  |
              Protocol Adapter    Tool Metadata
                    |
             Configured Model
```

The loader builds an in-memory registry. The resolver builds a read-only NetworkX graph. Context objects are immutable. Execution plans are inspectable and deterministic. AI invocation passes through UMAL, governance, and canonical protocol adapters. Tool recommendations pass through the same governance boundary. History, events, budgets, audit records, and artifacts remain in memory.

Frozen v0.6 layers are Runtime Foundation, Resolution, Context, Execution, UMAL, Invocation, Tool/MCP, Governance, CLI, and configuration.
