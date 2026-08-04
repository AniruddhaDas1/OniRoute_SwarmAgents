# OniRoute Universal Skill Import Engine

## Purpose

The Import Engine defines how external Skill packages are evaluated and admitted into OniRoute. It is an architecture and contract boundary, not a downloader, parser, installer, or runtime.

## Relationship to the Registry

The Import Engine prepares normalized provenance and metadata for Registry admission. The Registry remains the authority for indexed identity, versions, validation state, dependencies, compatibility, and installation state.

## Relationship to Normalization

Normalization maps source-specific layouts and metadata into the universal Skill Specification without changing authorship, license, provenance, or declared behavior. Normalization must be reviewable and reversible.

## Relationship to Validation

Validation evaluates schema, contracts, dependencies, compatibility, naming, licensing, and package integrity after normalization. Import does not bypass validation.

## Relationship to Future Runtime

The future Runtime may consume installed, validated Skills. Import architecture does not authorize execution, tool access, network access, or runtime loading.

## Boundaries

This phase creates no importers, network clients, parsers, installers, packages, repositories, or actual Skills.

## Documents

- [`IMPORT_PIPELINE.md`](IMPORT_PIPELINE.md) — lifecycle stages.
- [`IMPORTER_INTERFACE.md`](IMPORTER_INTERFACE.md) — common importer concepts.
- [`IMPORT_MANIFEST.md`](IMPORT_MANIFEST.md) — operation metadata.
- [`IMPORT_STATES.md`](IMPORT_STATES.md) — import state model.
- [`SOURCE_TYPES.md`](SOURCE_TYPES.md) — source characteristics and trust.
- [`ERROR_HANDLING.md`](ERROR_HANDLING.md) — failure and recovery guidance.
