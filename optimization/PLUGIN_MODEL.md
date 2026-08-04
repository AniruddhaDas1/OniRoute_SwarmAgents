# ICOE Plugin Model

## Plugin contract

Every plugin declares:

- Plugin ID, version, display name, provider, implementation class, lifecycle, trust, validation, and license.
- Supported optimization types and Context kinds.
- Input/output contracts, required capabilities, permissions, dependencies, configuration schema, and resource estimates.
- Determinism, lossiness, reversibility, provenance, protected-content behavior, and failure modes.
- Health, priority, compatibility, quality metrics, and benchmark evidence.

The common conceptual interface is **describe → supports → plan → transform candidate → validate → report**. Phase O1 defines this contract only; it does not create callable interfaces or plugins.

## Plugin classes

- **Native:** future OniRoute-maintained, dependency-minimal transformations.
- **RTK:** optional terminal-output Tool integration; full raw output remains recoverable and failure output is protected.
- **AST:** optional parser-backed symbol/function/class retrieval, independent of parser vendor.
- **Repository Graph:** optional dependency, impact, community, and flow retrieval.
- **Future Optimizer:** custom implementation admitted through the same governance and benchmark requirements.

## Isolation and governance

Plugins cannot call models, Tools, MCP servers, networks, shells, or storage merely by being selected. Such access requires existing OniRoute Tool/MCP, permission, approval, budget, security, and audit layers. Plugin failure falls back according to policy. Plugin output is untrusted until validation succeeds.
