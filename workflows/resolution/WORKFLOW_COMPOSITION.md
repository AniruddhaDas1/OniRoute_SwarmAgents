# Workflow Composition

- **Standalone Workflow:** complete contract with no composed Workflow dependency; use for one bounded outcome.
- **Composite Workflow:** contract formed from two or more compatible Workflow references; use for a coordinated outcome.
- **Nested Workflow:** a Workflow referenced within a bounded parent contract; use when a sub-outcome has its own lifecycle and ownership.
- **Reusable Workflow:** stable contract explicitly designed for reference by multiple parents.
- **Parameterized Workflow:** contract with declared parameters and constraints; use when variation does not alter ownership or safety boundaries.
- **Template Workflow:** incomplete structural contract intended for governed specialization; it is not an instance.
- **Reference Workflow:** metadata-only pointer to an authoritative Workflow record and version.

Composition must preserve each participant's responsibilities, provenance, approvals, security classification, and ownership. It must declare ordering, context mappings, artifacts, and conflict outcomes without prescribing implementation.
