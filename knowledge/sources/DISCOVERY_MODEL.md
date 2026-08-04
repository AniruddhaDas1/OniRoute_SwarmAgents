# Knowledge Source Discovery Model

## Automatic Discovery

Future connectors may discover registered origins and report candidate assets, revisions, licenses, and capabilities. Automatic discovery must be scoped, authenticated where required, rate-limited, and auditable.

## Manual Registration

An authorized owner may register a Source with explicit origin, trust claim, license, supported asset types, and revision. Manual registration still requires validation before availability.

## Scheduled Refresh

A future scheduler may refresh available Sources according to declared policy. Refresh records timestamps, revision, change summary, errors, and authorization context.

## Version Detection

Discovery compares branches, tags, commits, digests, release metadata, or source-defined versions. Mutable references must be resolved to immutable evidence before admission.

## Change Detection

Change detection identifies metadata, license, layout, asset, dependency, and compatibility changes. It must not silently normalize or import changed content.

## Duplicate Detection

Sources are compared by stable origin, canonical locator, owner, revision, digest, and declared identity. Duplicate records should link to a canonical Source rather than create conflicting provenance.

Discovery produces metadata and evidence only; import, normalization, Registry admission, and execution remain separate governed stages.
