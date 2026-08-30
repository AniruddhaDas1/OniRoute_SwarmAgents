# Universal AI Invocation Layer

Invocation routes Capability → UMAL Model → Protocol Adapter → Provider endpoint → Model. The Execution Engine remains isolated from providers. Requests and responses use canonical Pydantic contracts; adapters translate only at the protocol boundary.

OpenAI-compatible and Ollama adapters are the reference implementations. OpenAI-compatible local servers, LM Studio, vLLM, LocalAI, llama.cpp gateways, and other compatible services use the same adapter through configuration. Other protocols share the interface and may be implemented later without changing callers.

Routing uses UMAL capability, health, priority, locality, fallback, user, and environment metadata. Retry policies support Retry, Fallback, Fail Fast, Timeout, and Circuit Breaker declarations; current execution implements bounded retry/fail-fast behavior. Streaming exposes one iterator interface backed by **real provider streams**: OpenAI-compatible HTTP SSE and Ollama newline-delimited JSON each parse genuine incremental provider events. A literal `data: [DONE]` terminates an OpenAI stream and is never converted into a content chunk. Adapters that cannot stream yield a structured `streaming_unsupported` result rather than simulating streaming. See `docs/E1.5_RUNTIME_STREAMING.md`.
