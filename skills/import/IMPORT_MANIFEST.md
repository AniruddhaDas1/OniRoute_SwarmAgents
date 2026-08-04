# Import Manifest

An Import Manifest describes one attempted source-to-OniRoute operation. It is separate from the Skill metadata manifest and must include:

- Source type and source locator.
- Repository or archive identifier, when applicable.
- Branch, tag, or revision requested.
- Commit hash or immutable content digest when available.
- Declared and detected license.
- Import timestamp and initiating context.
- Imported Skill ID and version, when extracted.
- Original package layout and root path.
- Provenance and attribution evidence.
- Import state and validation summary.
- Normalization mapping and warnings.

The manifest is append-only evidence for the operation. It must not overwrite the source Skill metadata and must retain enough information to reproduce or audit the decision without requiring the source to remain online.
