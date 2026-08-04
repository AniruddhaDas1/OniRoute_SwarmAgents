# Metadata Verification

## Normalized entries

All 991 normalized Community manifests contain identifiers, author, license, repository, original path, commit, blob SHA, source URL, import timestamp, normalization version, tags, compatibility, trust level, validation state, lifecycle, and bounded non-executable contracts. Every normalized entry has a corresponding accepted record in its source `DECISIONS.yaml`.

The surrounding generated files contain only:

- canonical summary fields and compatibility classifications;
- source repository, author, path, revision, blob, URL, and license provenance;
- normalization and registration history;
- empty example and test placeholders;
- a short license/provenance notice.

No prompt body, code, documentation body, example, test, workflow, script, or asset deviates from the metadata-only boundary.

## Source catalogs

All nine top-level `IMPORT_METADATA.yaml` records contain repository URL, branch, commit, import timestamp, normalization version, license status, catalog status, validation boundary, source type, and `copied_source_content: false`. Owner identity is recoverable from the canonical repository URL and is explicit in normalized `author`/`organization` fields, but top-level import records do not have a dedicated `owner` key. This is a documentation-level metadata deviation, not missing provenance and not authorization to change the frozen schema.

`andrej-karpathy-skills` has a rejection decision for its single candidate. `skillfish` has no candidate decision record because zero Skills were imported; its import metadata and source record establish catalog-only provenance.
