# Import Pipeline

The universal import lifecycle is an auditable sequence. Each stage produces evidence for the next stage and may stop the operation without mutating the Registry.

1. **Source Discovery** — identify source type, locator, trust context, and requested revision.
2. **Package Detection** — determine whether a supported Skill package layout exists.
3. **Manifest Extraction** — locate and read the source manifest without assuming a provider format.
4. **Metadata Extraction** — collect identity, version, author, organization, compatibility, dependencies, and provenance.
5. **License Detection** — identify declared license and attribution obligations.
6. **Compatibility Analysis** — compare declared Agents, sub-agents, tools, context, providers, and version constraints.
7. **Normalization** — map source metadata to the universal Skill Specification while preserving original values and paths.
8. **Registry Admission** — submit the normalized record for duplicate, version, provenance, and policy checks.
9. **Validation** — run schema, contract, dependency, license, compatibility, naming, and integrity checks.
10. **Installation** — make an approved package available to the local Skill store; installation remains a future capability.

Every transition records state, timestamp, source revision, evidence, and responsible policy decision. Failures are terminal for the attempted revision until explicitly retried or rejected.
