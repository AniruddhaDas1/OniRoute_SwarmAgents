# Universal Tool and MCP Engine

The Tool Engine describes local tools and MCP servers through one provider-independent metadata layer. The in-memory registry contains tools, local tools, MCP servers, protocols, capabilities, and aliases. Selection evaluates capabilities, permissions, health, trust, lifecycle, protocol, provider, preference, and priority.

Permissions are declarations evaluated against configuration policy; they do not grant operating-system authority. MCP records describe servers, transports, authentication types, and available tools without connecting. A future execution layer may implement separate, explicitly authorized adapters. This phase performs no tool execution, filesystem modification, shell command, browser automation, database operation, authentication, secret access, SDK call, network request, or MCP communication.
