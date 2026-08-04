# Admission Decision Records

Each decision records canonical identity and version, source and provenance, normalized metadata, validation evidence, dependency and compatibility findings, license status, policy version, decision authority, timestamp, and remediation or successor guidance.

## Outcomes

- **Accepted** — meets gates and may enter the Registry.
- **Rejected** — fails a mandatory gate; not eligible for admission.
- **Quarantined** — retained for investigation and excluded from normal discovery.
- **Needs Review** — ambiguity or policy judgment prevents an automatic decision.
- **Duplicate** — identity/version or content matches an existing record; no second canonical record is created.
- **Superseded** — replaced by a newer or designated successor while provenance remains retained.

Decision records are append-only. A changed source or normalization version creates a new decision linked to earlier records.
