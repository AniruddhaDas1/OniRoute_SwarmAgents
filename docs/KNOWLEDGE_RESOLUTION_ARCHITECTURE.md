# Knowledge Resolution Architecture

## Permanent Resolution Order

```text
Official OniRoute Skill
        ↓
Official Package Skill
        ↓
Verified Community Skill
        ↓
Community Skill
        ↓
Missing Capability
        ↓
Recommendation
```

This is the unique OniRoute resolution order. A lower tier is consulted only when no higher-tier candidate passes trust, lifecycle, compatibility, evidence, dependency, and policy gates.

## Resolver Lifecycle

1. Receive Agent, optional Sub-Agent, capability, context, trust, version, and policy constraints.
2. Read the external Agent–Skill Resolution Index.
3. Evaluate eligible candidates in permanent tier order.
4. Filter by compatibility, lifecycle, trust, validation evidence, freshness, and dependencies.
5. Rank candidates by exact mapping and evidence-backed confidence.
6. Select one candidate or a reviewed composition.
7. Apply fallback only within policy.
8. Return a decision record, Missing Capability, or Recommendation.

## Trust Propagation

Trust is evaluated per Source, Package, and Skill. It does not automatically propagate across containment or provenance. Official status does not bypass compatibility or evidence. Community mappings remain Low confidence until reviewed.

## Confidence Scoring

Confidence is High, Medium, Low, or None. It considers exact Agent/Sub-Agent fit, evidence type and freshness, ownership, provenance, license, validation, contracts, dependencies, lifecycle, and source review. Numeric quality scores are secondary to evidence.

## Fallback Logic

Deprecated knowledge prefers an eligible successor. Disabled, archived, removed, incompatible, or unresolved candidates are excluded. Equal candidates produce deterministic evidence or a review request. No candidate produces Missing Capability followed by a non-executable Recommendation.

## Promotion Flow

Community → reviewed Community → Verified Community → newly authored Official knowledge only after validated production gap or architecture approval. Promotion preserves provenance and creates an append-only decision; resolution itself cannot promote.

## Deprecation Flow

Active → Deprecated with reason, successor, compatibility window, and migration guidance → Archived or Removed with retained audit evidence. Resolver caches invalidate at every lifecycle change.

## Refresh Flow

Source or asset revision → metadata change detection → provenance/license/trust review → validation evidence refresh → mapping and dependency review → decision record → cache invalidation. Refresh never imports or executes content automatically.

## Canonical Registries

- Agent mappings: `mappings/agent-skills/RESOLUTION_INDEX.yaml`
- Knowledge Sources: `knowledge/sources/registry/REGISTERED_SOURCES.yaml`
- Evidence framework: `knowledge/validation/`
- Governance: `knowledge/governance/`
