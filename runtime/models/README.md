# Universal Model Abstraction Layer

UMAL resolves model metadata through Capability → Protocol → Adapter → Provider → Model. Its catalog and registry are in memory, provider names are configuration data, and selection is a deterministic metadata score over capabilities, protocol compatibility, availability, priority, local preference, health, fallback order, user preference, and environment preference.

UMAL provides provider-independent model selection across capabilities, protocols, adapters, and providers. Execution never hardcodes providers. Protocol translation and model adapter execution are handled through the Invocation Layer (`runtime/invocation/`), supporting provider-agnostic execution with policy control.
