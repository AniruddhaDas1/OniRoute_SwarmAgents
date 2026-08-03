# Configuration

This directory is reserved for configuration that composes the organization and its agents across environments.

Configuration should be declarative, minimal, and safe to commit. Keep secrets and machine-local values outside the repository; provide documented examples when a setting is required. Provider-specific details should be isolated behind explicit adapters so the core architecture remains vendor-independent.

Future configuration may cover organization topology, enabled agents, model providers, context limits, and observability defaults. Those schemas should be introduced only with accompanying documentation and validation.
