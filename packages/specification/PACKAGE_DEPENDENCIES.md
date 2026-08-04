# Package Dependencies

- Required dependencies must resolve before installation eligibility.
- Optional dependencies must declare degraded behavior when absent.
- Circular package dependencies are rejected.
- Version ranges must use compatible semantic constraints.
- Conflicts require deterministic resolution or review; silent replacement is prohibited.
- Replacement Packages require explicit successor, migration, compatibility, and provenance evidence.
- Deprecated dependencies are allowed only for migration or existing compatibility policy.

Dependency admission does not install or execute Packages.

