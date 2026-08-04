# Optimization Policies

Policies define allowed modules, protected fields, maximum lossiness, minimum quality, budget targets, recovery requirements, plugin trust, security classification, and approval requirements.

## Policy rules

- **Never remove:** system/security constraints, approvals, explicit user requirements, ownership, licenses, provenance, failure evidence, and output contracts unless a governing contract explicitly permits transformation.
- **Budget:** reserve space for model output, Tool results, and safety overhead; a budget is a ceiling, not a target to fill.
- **Loss:** lossy transformations require measurable quality evidence, a declared threshold, and original/less-lossy fallback.
- **History decay:** age lowers rank but does not override unresolved decisions, repeated user intent, or audit retention.
- **Terminal safety:** successful noise may collapse; failures and stderr require stronger retention.
- **Retrieval:** indexes must expose freshness, scope, language coverage, confidence, and provenance. Absence from an incomplete/stale index is not proof of absence.
- **Plugins:** unknown, unhealthy, incompatible, or unvalidated plugins are excluded. External access follows runtime governance.
- **Audit:** every transformation records source hashes/references, plugin version, policy, removed/retained classes, estimates, and validation outcome.

## Fallback order

Validated optimized candidate → less aggressive candidate → retrieval-only candidate → original Context within budget → explicit over-budget/blocked result. Fallback never bypasses security or approval policy.
