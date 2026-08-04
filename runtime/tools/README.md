# Universal Tool and MCP Engine

The Tool Engine describes local tools and MCP servers through one provider-independent metadata layer. The in-memory registry contains tools, local tools, MCP servers, protocols, capabilities, and aliases. Selection evaluates capabilities, permissions, health, trust, lifecycle, protocol, provider, preference, and priority.

The Tool Layer defines available local tools and MCP integrations. Tool access and capabilities are policy-controlled and governed by the Governance Layer. Tool metadata is intentionally separated from tool execution mechanisms to maintain security and provider independence.
