# OniRoute Skill Specification

## Purpose

This directory defines the universal metadata and governance contract for every future OniRoute Skill. It defines what a Skill is, how it differs from Agents and Workflows, and how internal or imported skills become governed OniRoute Skills.

## What is a Skill?

A Skill is a reusable, bounded capability contract that may later be attached to an Agent or Workflow. This phase defines metadata and governance only; it does not define skill content or execution.

## Skills, Agents, and Workflows

- An Agent owns a responsibility and provides organizational direction.
- A Skill provides a reusable capability that can support an Agent.
- A Workflow defines coordinated sequencing across responsibilities.

Skills do not replace Agents and do not become executable merely by conforming to this specification.

## Imported Skills

Skills may originate from GitHub, Git, ZIP archives, local folders, or future registries. Importing preserves provenance, authorship, licensing, original path, and version. An imported artifact becomes an OniRoute Skill only after metadata, contract, compatibility, dependency, and license validation.

## Documents

- [`skill.schema.yaml`](skill.schema.yaml) — metadata schema.
- [`SKILL_CONTRACT.md`](SKILL_CONTRACT.md) — behavioral contract fields.
- [`SKILL_LIFECYCLE.md`](SKILL_LIFECYCLE.md) — lifecycle states and transitions.
- [`VERSIONING.md`](VERSIONING.md) — semantic versioning rules.
- [`LICENSE_POLICY.md`](LICENSE_POLICY.md) — provenance and license requirements.
- [`IMPORT_POLICY.md`](IMPORT_POLICY.md) — supported import sources and boundaries.
- [`VALIDATION_RULES.md`](VALIDATION_RULES.md) — acceptance checks.

This specification does not create skills, packs, importers, runtimes, or provider integrations.
