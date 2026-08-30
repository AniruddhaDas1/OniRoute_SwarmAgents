# Runtime Kernel Freeze v1.2.1 (E1.7)

**Certification verdict: RUNTIME FREEZE — PASSED**

This document freezes the OniRoute Core v1.2.1 Agent Runtime Kernel completed
through E1.6. E2-E9 MUST consume this runtime through its existing contracts
and MUST NOT modify frozen architecture without an explicit exception.

## 1. Runtime purpose

The E1 runtime kernel executes agent/engineering work through a
provider-agnostic capability-based invocation layer:

- Agents request **capabilities**, never a specific provider/model.
- UMAL/ModelSelector resolves capabilities to a compatible model.
- Protocol adapters translate InvocationRequest/Response to provider protocols.
- EngineeringWorker orchestrates multi-step InvocationTasks through the kernel.

## 2. Frozen architecture

```
AgentProfile / EngineeringContract
            ↓
EngineeringWorkerEngine (InvocationPlanner → ExecutionBatch → ResponseAggregator)
            ↓
InvocationEngine.invoke()/stream()   ← runtime gateway
            ↓
InvocationRouter → UMAL/ModelSelector ← model-selection authority
            ↓
ProtocolAdapter (OpenAI-compatible | Ollama | InterfaceOnly)
            ↓
Provider
```

## 3. Public contracts (FROZEN)

| Contract | Module | Status |
|----------|--------|--------|
| InvocationRequest | runtime/invocation/request.py | FROZEN |
| InvocationResponse | runtime/invocation/response.py | FROZEN |
| Message, Usage | runtime/invocation/models.py | FROZEN |
| StreamChunk, StreamUsage, StreamFinishReason | runtime/invocation/models.py | FROZEN |
| SelectionRequest, ModelRecord, ProviderRecord, ProtocolRecord | runtime/models/models.py | FROZEN |
| Capability | runtime/models/capabilities.py | FROZEN |
| TaskState, TaskContext, InvocationTask, ExecutionBatch, BatchResult, EngineeringResult | runtime/engineering/models.py | FROZEN |
| StreamEvent, StreamEventType | runtime/experience/models.py | FROZEN |

## 4. State machine (FROZEN)

```
Queued
  ↓
Ready
  ↓
Running
  ├── Completed    (terminal)
  ├── Failed       (terminal)
  ├── Blocked      (terminal)
  ├── Skipped      (terminal)
  └── Cancelled    (terminal)
```

Plus an intermediate `Waiting` state:

```
Ready → Waiting → Running → Waiting → Running | Failed | Cancelled
```

Invalid transitions raise `ValueError`. Terminal states reject all transitions.

## 5. Invocation boundary (FROZEN)

- EngineeringWorker/agents request capabilities through `InvocationRequest`.
- They do NOT call providers directly.
- They do NOT select models directly.
- `InvocationEngine` is the only runtime gateway.
- `InvocationRouter` + `ModelSelector` own model selection.
- `ProtocolAdapter` owns protocol translation.

## 6. Provider boundary (FROZEN)

Only two real protocol adapters exist:

| Adapter | Protocol | Non-streaming | Streaming |
|---------|----------|---------------|-----------|
| OpenAICompatibleAdapter | openai-compatible | Yes | Yes (SSE) |
| OllamaAdapter | ollama | Yes | Yes (ndjson) |
| InterfaceOnlyAdapter | custom | No | No |

All other provider names in `runtime/models/providers.py` are catalog
metadata, not runtime integrations.

## 7. Streaming boundary (FROZEN)

- `InvocationEngine.stream()` delegates to `ProtocolAdapter.stream()`.
- `invoke()` is NEVER used as a fake streaming implementation.
- OpenAI `[DONE]` terminates the stream without producing a chunk.
- Ollama `done` event yields a terminal chunk with real usage.
- No synthetic terminal chunks are generated.
- Chunk ordering is deterministic (monotonic sequence).
- Stream failures raise `StreamConnectionError`; partial content is preserved
  as diagnostic state, never certified as successful generation.

## 8. ExecutionContext (FROZEN)

`TaskContext` preserves through the entire runtime path:

mission_id, workspace_id, blueprint_id, engineering_contract_id,
execution_batch_id, invocation_task_id, agent_profile_id, skill_bundle_id,
repository_context, execution_constraints, execution_priority.

## 9. Accounting (FROZEN)

- Real provider usage (prompt_tokens, completion_tokens, total_tokens) is
  carried from provider terminal events.
- When a provider emits no usage, accounting is `0`/absent — never fabricated.
- Cost remains `0.0` (no real cost signal from local providers).

## 10. Verified capabilities

- **OpenAI-compatible**: non-streaming + streaming SSE, usage parsing,
  finish-reason parsing, auth header support — VERIFIED (deterministic mocked).
- **Ollama**: non-streaming + streaming ndjson, usage parsing,
  finish-reason parsing, auth header support — VERIFIED (deterministic mocked).
- **Two-provider interoperability**: MOCK-VERIFIED (E1.6 decoupling test).

## 11. Known limitations

1. Only 2 real protocol adapters: OpenAI-compatible and Ollama.
2. Only 1 configured model: `local-metadata-placeholder` (custom/local-process).
3. No automatic provider-failure fallback in `InvocationEngine`.
4. Real provider smoke tests are opt-in, not CI-required.
5. Tool-calling, vision, and structured-output are declared in catalog
   metadata but have no adapter implementation in E1.

## 12. Extension rules

E2-E9 may:

- Add new protocol adapters (implementing `ProtocolAdapter`).
- Add new provider/model entries to `config/models.yaml`.
- Add new capabilities to `Capability` enum (with catalog migration).
- Consume frozen contracts via import.

E2-E9 MUST NOT:

- Modify frozen contracts without an architectural exception.
- Add provider-specific logic to agents or EngineeringWorker.
- Add a second InvocationEngine or streaming engine.
- Add retries/self-healing/dynamic contracts in E1.

## 13. Prohibited modifications

- Do not add a new InvocationEngine or a second streaming engine.
- Do not add provider-specific logic inside agents or EngineeringWorker.
- Do not add a new UMAL, ModelSelector, or provider registry.
- Do not add retries, self-healing, or dynamic contracts in E1.
- Do not change frozen contracts without an architectural exception.

## 14. E2-E9 integration rules

1. Import frozen contracts from their canonical modules.
2. Request capabilities, never provider/model names.
3. Use `InvocationEngine.invoke()`/`stream()` as the only invocation gateway.
4. Read `EngineeringResult`/`BatchResult`/`TaskContext` as immutable inputs.
5. Do not subclass or monkeypatch frozen runtime internals.

## 15. Certification evidence

- E1.1-E1.6 implementation history: 6 commits on v1.2.1 series.
- E1.6 verification suite: 66 tests, 0 failures.
- E1.7 freeze guards: 12 tests, 0 failures.
- E1.7 state machine: 6 tests, 0 failures.
- E1.7 freeze manifest: 7 tests, 0 failures.
- Full regression: recorded in E1.7 final report.
- `git diff --check`: CLEAN.
- YAML/Markdown validation: PASS.
- `oniroute doctor`: PASS.
- Package build: SUCCESS.

## Certification verdict

**RUNTIME FREEZE — PASSED**
