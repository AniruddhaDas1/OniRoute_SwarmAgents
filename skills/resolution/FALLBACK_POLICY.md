# Fallback Policy

- **Missing Skill** — report unmet capability; search approved replacements or require review rather than silently substituting.
- **Deprecated Skill** — prefer its declared successor; permit existing compatibility only with migration evidence.
- **Unavailable Skill** — distinguish not installed, disabled, archived, removed, or inaccessible and return actionable status.
- **Conflicting Skill** — reject incompatible contracts or dependency graphs; do not compose contradictory candidates.
- **Multiple Equal Skills** — return deterministic tie evidence, request policy selection, or present alternatives; never hide the tie.

Fallbacks must preserve the original request, disclose changed capability or quality, and record the selected alternative and rationale. No fallback bypasses license, validation, compatibility, or lifecycle gates.
