# Registry Lifecycle

Registry installation states describe local catalog and availability status:

- **Available** — discoverable and eligible for installation review.
- **Installed** — package is present in the local Skill store.
- **Disabled** — installed but intentionally unavailable to consumers.
- **Deprecated** — retained for migration with a warning or successor.
- **Archived** — retained for historical provenance and not eligible for normal use.
- **Removed** — withdrawn from active registry views; audit metadata may remain retained.

State transitions require provenance, validation, dependency, license, and compatibility evidence. Installed does not mean enabled, validated, or executable. Removal must preserve auditability and version history where policy or license permits.
