# Security Policy

## Reporting

Report suspected vulnerabilities privately through the repository's GitHub Security Advisory channel. Do not publish exploit details in a public issue. If private advisories are not enabled for the repository, maintainers must enable them or publish a monitored private contact before a stable release. No maintainer email address is asserted by this repository.

Include the affected version or commit, a minimal reproduction, impact, relevant logs with secrets removed, and any suggested mitigation. Never include credentials, tokens, personal data, or production endpoints.

## Scope and limitations

The v1.0.0 scope covers the Python runtime, CLI, metadata loading and validation, workflow planning/execution, governance checks, and packaged distribution. Community records and external research links are provenance metadata, not executable dependencies. OniRoute stores no secrets and provides no secrets manager. Automatic AI invocation must be explicitly enabled and governed. Tool/MCP execution is not implemented in runtime v0.6.

Security reports are triaged by the maintainers. Acknowledgement, remediation, and disclosure timing depend on report quality, exploitability, and maintainer availability.
