# Workflow Resolution

Resolution transforms a Workflow Request and admitted registry metadata into a resolved Workflow description. It produces metadata only and never invokes a participant or dependency.

## Canonical order

1. **Workflow Request** — declare outcome, constraints, context, and policy.
2. **Registry Search** — identify candidate records by metadata.
3. **Compatibility Evaluation** — compare Agents, Skills, Packages, platforms, versions, artifacts, and security constraints.
4. **Dependency Validation** — validate declared dependency identity, version, provenance, and lifecycle.
5. **Conflict Detection** — identify duplicate IDs, incompatible versions, cycles, ownership, skills, packages, or gates.
6. **Composition** — assemble permitted standalone, nested, referenced, or parameterized contracts.
7. **Approval Requirements** — calculate declared approval gates and evidence requirements.
8. **Resolved Workflow** — record selected versions, composition, context, branches, dependencies, conflicts, approvals, and evidence.

This order is normative and unique. A failure at any step yields a declared resolution state or fallback; it cannot silently bypass policy or reorder gates.
