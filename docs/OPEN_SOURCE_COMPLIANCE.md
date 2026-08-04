# Open Source Compliance

Audit date: 2026-08-04. Scope: v1.0.0 repository tree, declared Python dependencies, community metadata, research references, governance documents, and release procedures.

## Assessment

The project code and documentation are Apache-2.0-licensed and provider-independent. Community imports are metadata-only and preserve source URLs, authorship fields, revisions, and declared licenses. Official Skills and workflows are OniRoute-authored; their `references.md` files cite concepts without copying implementation, prompts, examples, documentation, or repository structure.

The audit does not approve distribution of content whose license is unresolved. `skillfish` is declared AGPL-3.0, `andrej-karpathy-skills` has an unresolved license, and Popmotion is cited as research with no confirmed license in the registry. These are review-gated and block a public stable release until a maintainer decides whether they are excluded, reference-only, or separately noticed.

## Decision

The prior third-party blockers are resolved by explicit release decisions: Skillfish and Popmotion remain reference-only, and the unknown-license Karpathy source remains excluded from admission. Final certification evidence is recorded in `docs/V1_RELEASE_CERTIFICATE.md`.

## Evidence

- Root `LICENSE` is Apache License 2.0; `pyproject.toml` declares SPDX `Apache-2.0`.
- `docs/THIRD_PARTY_NOTICES.md` enumerates all nine community metadata sources.
- `docs/LICENSE_COMPLIANCE_MATRIX.md` records every dependency and external repository decision.
- `docs/SECURITY.md` defines reporting scope and process, but a monitored maintainer contact/private-advisory channel must be confirmed before stable release.
- Existing CI, governance templates, versioning, release, and freeze documents are present.
