# Metadata Mapping

Foreign metadata maps to the universal schema through explicit, provider-independent rules:

| Source concept | Canonical field | Mapping rule |
|---|---|---|
| Stable identifier | `id` | Lowercase and validate; preserve original identifier in provenance. |
| Human title | `name`, `display_name` | Retain meaning; use display formatting only for presentation. |
| Summary | `description` | Normalize whitespace; do not expand claims. |
| Domain label | `category` | Map to an approved category vocabulary; retain unmapped value as evidence. |
| Keywords | `tags` | Lowercase, trim, deduplicate, and preserve unknown tags with review status. |
| Release string | `version` | Normalize to Semantic Versioning or mark for review; never invent precedence. |
| License declaration | `license` | Map recognized SPDX-like identifiers or retain declared text pending review. |
| Audience declaration | `compatible_agents`, `compatible_sub_agents` | Resolve only against known catalog identities; unresolved names require review. |
| Input/output descriptions | `input_contract`, `output_contract` | Preserve contract meaning and identify missing structure. |
| Tool/context lists | `required_tools`, `optional_tools`, `consumes_context`, `produces_context` | Normalize names and required/optional semantics without adding capabilities. |
| Dependency declarations | `dependencies`, `related_skills` | Resolve stable IDs and version ranges; retain unresolved references. |
| Provider references | `compatibility` and registry provider metadata | Record explicit assumptions without leaking them into universal rules. |

No mapping may silently change author, license, source, version, ownership, or declared behavior. Ambiguous mappings produce `Needs Review` evidence.
