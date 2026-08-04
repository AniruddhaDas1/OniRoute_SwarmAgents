# Mapping Audit

## Coverage Chain

Agent → Official Skill mappings cover 76 Agents. Agent → Community Skill mappings cover 79 Agents. Combined unique coverage reaches 112 Agents. Package Skill mappings cover none.

## Findings

- 173 Agents have no Skill mapping.
- 33 have Official-only coverage, 36 Community-only, and 43 mixed coverage.
- All 88 Official and 991 Community Skills have at least one declared mapping.
- Agent YAML `skills` arrays are empty, so mappings are one-directional from Skills.
- Ten Agents have over 500 Community mappings, indicating systematic overmapping.
- Specialized Platform sub-agents are the largest undermapped group.

## Resolver Risk

The resolver architecture can rank metadata, but mapping confidence, reciprocal declarations, semantic compatibility, and reviewed dependencies are insufficient for production resolution.
