# Resolution Cache Policy

Resolution caches may store request predicates, Registry revision, selected Skill IDs and versions, dependency expansion, ranking evidence, context fingerprint, policy version, and result timestamp. They must not become an authority independent of the Registry.

Invalidate or re-resolve when:

- A selected Skill or dependency version changes.
- Registry records, validation state, lifecycle, license, or compatibility change.
- Agent or sub-agent compatibility changes.
- Resolution policy, ranking weights, or license policy changes.
- Required context, tools, provider, or environment changes.
- Cache TTL or freshness policy expires.

Stale results must be marked stale, never silently reused. Cache keys must exclude sensitive context or use an approved privacy-preserving fingerprint.
