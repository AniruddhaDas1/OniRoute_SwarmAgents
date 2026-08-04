# Normalization Pipeline

1. **Receive import evidence** — accept the Import Manifest, source metadata, and original layout.
2. **Establish canonical identity** — derive a stable ID without silently replacing an authoritative source identifier.
3. **Map metadata** — transform fields to the universal Skill Specification.
4. **Normalize controlled values** — canonicalize category, tags, version, license, compatibility, dependencies, context, and provider references.
5. **Preserve provenance** — attach original values, paths, revisions, and timestamps.
6. **Resolve dependencies** — identify required, optional, replacement, deprecated, missing, circular, and conflicting dependencies.
7. **Evaluate compatibility** — compare Agent, sub-agent, context, tool, provider, and future Workflow contracts.
8. **Produce decision evidence** — emit a mapping report, warnings, unresolved questions, and a proposed canonical record.
9. **Apply admission policy** — accept, reject, quarantine, or request review.
10. **Submit to Registry** — submit only accepted normalized metadata; installation eligibility remains a separate state.

Normalization is deterministic where source evidence is unambiguous, reviewable where interpretation is required, and reversible through preserved source values and mapping decisions.
