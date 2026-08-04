# Import Error Handling

Errors are classified, recorded in the Import Manifest, and surfaced without silently repairing source intent.

- **Unsupported layouts** — reject with the expected package contract and detected paths.
- **Missing metadata** — pause or reject; request authoritative values rather than infer identity, version, compatibility, or license.
- **License conflicts** — block admission when declared, detected, or policy-required licenses disagree.
- **Duplicate Skills** — compare stable ID, version, source, and digest; require explicit deduplication or coexistence policy.
- **Dependency conflicts** — report incompatible ranges, cycles, unavailable dependencies, and provider constraints.
- **Version conflicts** — reject ambiguous or non-semantic versions; preserve source version history and require migration review for breaks.
- **Schema mismatches** — retain source evidence, produce a normalization report, and block validation until required fields conform.
- **Corrupted packages** — fail integrity checks, quarantine the attempt, and never install partially inspected content.

Recovery is policy-driven: retry only with a new attempt record, quarantine suspicious content, and preserve audit evidence. Importers must not bypass errors by silently changing source files or metadata.
