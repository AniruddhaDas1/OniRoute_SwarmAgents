# Registry Indexing

The Registry maintains an index keyed by `(skill_id, version)` and a current-version pointer per Skill ID. Version history remains immutable; updates add records rather than rewriting prior evidence.

## Indexed Dimensions

Index fields support lookup by:

- Skill ID
- Tags
- Category
- Compatible Agent
- Compatible sub-agent
- Author
- License
- Provider
- Validation state
- Version

Secondary indexes may be materialized for compatibility, dependencies, quality score, installation status, lifecycle class, and source. Index updates occur after validation and provenance capture. Stale or failed records remain queryable with their state visible.
