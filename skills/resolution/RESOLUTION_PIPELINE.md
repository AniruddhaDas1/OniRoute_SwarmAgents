# Resolution Pipeline

1. **Agent Request** — capture Agent, sub-agent, capability, context, tool, license, lifecycle, and version constraints.
2. **Capability Discovery** — translate the request into explicit capability and compatibility predicates.
3. **Registry Search** — query Registry metadata and provenance without selecting by name alone.
4. **Compatibility Filtering** — remove records incompatible with Agent, sub-agent, context, tools, dependencies, policy, or installation state.
5. **Dependency Expansion** — include required dependencies and evaluate optional, replacement, deprecated, and conflicting dependencies.
6. **Ranking** — order eligible candidates using declared policy and evidence.
7. **Composition** — assemble atomic Skills or approved composite structures while preserving boundaries.
8. **Resolution Result** — return selected records, rejected alternatives, dependencies, assumptions, provenance, confidence, and unresolved risks.

Resolution is advisory until a future Runtime or Workflow explicitly consumes the result. Every result is traceable to Registry versions and the request context used.
