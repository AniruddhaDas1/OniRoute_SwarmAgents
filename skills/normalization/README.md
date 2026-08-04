# Skill Normalization & Admission Engine

## Purpose

Normalization transforms source-specific Skill metadata into canonical OniRoute metadata. Admission decides whether the normalized record may enter the Registry. Both are governance boundaries; neither executes, installs, or creates a Skill.

## Relationship to the Import Engine

The Import Engine supplies source evidence and an Import Manifest. Normalization maps that evidence without erasing provenance. Admission consumes the normalized record and validation evidence.

## Relationship to the Registry

The Registry is the destination and authority for accepted identity, versions, dependencies, compatibility, quality, and lifecycle state. Admission may submit a record; it does not bypass Registry policy.

## Relationship to the Future Runtime

Only an explicitly installed and runtime-compatible Skill may later be consumed by a Runtime. Normalization and admission do not authorize execution or tool access.

## Boundaries

No repositories are imported, parsers or installers are implemented, packages are created, or actual Skills are defined in this phase.

## Documents

- [`NORMALIZATION_PIPELINE.md`](NORMALIZATION_PIPELINE.md) — canonical transformation stages.
- [`METADATA_MAPPING.md`](METADATA_MAPPING.md) — source-to-canonical mapping.
- [`PROVENANCE.md`](PROVENANCE.md) — immutable source history.
- [`ADMISSION_POLICY.md`](ADMISSION_POLICY.md) — admission gates.
- [`DECISION_RECORD.md`](DECISION_RECORD.md) — outcomes and evidence.
- [`COMPATIBILITY_RULES.md`](COMPATIBILITY_RULES.md) — compatibility evaluation.
- [`DEPENDENCY_RESOLUTION.md`](DEPENDENCY_RESOLUTION.md) — dependency strategy.
