# Dependency Resolution

Dependency analysis produces a graph of Skill IDs, versions, and optionality before admission.

- **Missing dependencies** — block acceptance of required dependencies; optional gaps require an explicit degraded-capability decision.
- **Circular dependencies** — reject cycles unless a future contract explicitly defines a safe non-cyclic boundary.
- **Version conflicts** — resolve compatible ranges; otherwise reject or request a declared replacement.
- **Optional dependencies** — record separately and never treat them as silently required.
- **Replacement Skills** — prefer an explicitly designated successor with preserved provenance and migration guidance.
- **Deprecated Skills** — permit only for existing consumers or migration review; do not introduce new unapproved dependencies.

Resolution must be deterministic, explain selected versions, preserve alternatives, and record unresolved constraints in the decision record. Dependency admission does not install or execute any dependency.
