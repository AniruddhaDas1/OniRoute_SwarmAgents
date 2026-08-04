# Community Skill Audit

## Summary

- Accepted metadata Skills: 991
- Rejected candidates: 15
- Exact duplicate blobs rejected during import: 14
- Missing provenance fields: 0
- Missing license metadata in accepted records: 0
- Unmapped accepted records: 0
- Validation state: all accepted records remain `Needs Review`
- Initial quality score: 60 for all accepted records

## Provenance and Licensing

Accepted records preserve repository, path, commit, blob, source URL, timestamps, normalization version, original-version status, author, and license identifier. Full license-text applicability and per-path exceptions have not been audited.

## Mapping Quality

Mappings are path-keyword heuristics. They guarantee at least one Agent and Sub-Agent but are not production quality: broad categories map hundreds of unrelated candidates to Frontend, Testing, Platform, DevOps, Backend, Documentation, Security, Database, and Engineering Director.

## Promotion Candidates

Candidates from focused repositories such as `vuejs-ai/skills`, `mattpocock/skills`, and selected scoped entries from `gstack` may be easier to review. No candidate should be promoted solely from metadata.

## Repository Health Risks

Repository revisions are pinned at import time, but deprecation and upstream health are not refreshed. The unlicensed Karpathy source was rejected; the AGPL Skillfish source was cataloged but not imported.
