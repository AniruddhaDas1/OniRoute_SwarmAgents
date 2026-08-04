# Skill Validation Rules

Before acceptance, validate:

## Schema

- All required metadata fields are present.
- Field types, identifier pattern, status enum, timestamps, and quality-score range are valid.
- No undeclared metadata is treated as contract behavior.

## Metadata

- Name and display name are clear and non-misleading.
- Description and category match the declared capability.
- Author, organization, source, license, version, and dates are traceable.

## Dependencies

- Dependencies exist or are explicitly marked unavailable.
- Cycles, incompatible versions, missing tools, and unsupported context are rejected.

## Contracts

- Purpose, inputs, outputs, preconditions, postconditions, failure conditions, expected behavior, and non-goals are declared.
- Input and output contracts are compatible with consuming and compatible Agents.

## Naming

- `id` is lowercase, stable, unique, and semantic-version independent.
- Names do not impersonate Agents, Workflows, providers, or official status.

## Compatibility

- Declared Agents, sub-agents, context, tools, and platform assumptions are supported.
- Provider-specific requirements remain explicit and do not leak into the universal contract.

Validation results must be recorded before promotion beyond Draft.
