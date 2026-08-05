# Execution Experience Specification (Phase P6.D2)

## 1. Overview

The **Execution Experience** provides a presentation-agnostic streaming and rendering layer for OniRoute Engine v1.2 without altering underlying runtime execution logic or contract schemas.

```
Runtime Execution Events
          │
          ▼
ExecutionEventStream (Pub/Sub)
          │
          ▼
  PresentationAdapter (Channel Formatter)
   ├── CLI Renderer (Rich Output & Live Spinners)
   ├── VS Code Extension Adapter (JSON Events)
   ├── Web UI Adapter (SSE Payload)
   └── API Adapter (REST/gRPC Event Stream)
```

---

## 2. Decoupled Architecture

1. **`ExecutionEventStream`**: Publishes immutable `StreamEvent` contracts onto a thread-safe pub/sub event bus with optional trace persistence in `.oniroute/traces/`.
2. **`PresentationAdapter`**: Decouples UI formatting from runtime execution. Formats events specifically for CLI, VS Code, Web UI, and API.
3. **`ExecutionRenderer`**: Converts stream events into rich CLI progress bars, active agent spinners, live counters (tokens, cost, files), and Rich summary tables.
4. **`SessionRecoveryWatcher`**: Enables session status querying (`oniroute status`) and live trace watching (`oniroute watch`).
