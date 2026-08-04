# Universal Model Abstraction Layer

UMAL resolves model metadata through Capability → Protocol → Adapter → Provider → Model. Its catalog and registry are in memory, provider names are configuration data, and selection is a deterministic metadata score over capabilities, protocol compatibility, availability, priority, local preference, health, fallback order, user preference, and environment preference.

Protocols and providers are declarations only. Adapters are disabled metadata placeholders for a future phase. UMAL performs no inference, SDK calls, authentication, API requests, streaming, tools, MCP communication, or networking.
