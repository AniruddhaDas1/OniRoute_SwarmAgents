# Composition Model

- **Atomic Skills** — one bounded capability selected against one contract.
- **Composite Skills** — governed bundles with declared inputs, outputs, dependencies, and compatibility; composition does not merge ownership.
- **Expert Packs** — curated collections for an Agent or sub-agent, versioned and reviewed as a unit while retaining member provenance.
- **Dependency chains** — required Skills expanded in dependency order with cycle and version checks.
- **Replacement Skills** — explicit successors selected during migration or fallback, with rationale and compatibility evidence.

Composition must preserve each Skill's identity, license, provenance, version, non-goals, and failure conditions. A composite cannot broaden an Agent's authority or conceal a dependency. Future Workflows may sequence a resolved composition, but resolution does not execute it.
