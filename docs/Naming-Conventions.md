# Naming Conventions

Names must be stable, descriptive, provider-independent where practical, and consistent across documentation and future machine-readable definitions.

## Departments

- Department directories use lowercase singular names: `executive`, `engineering`, and `platform`.
- Department documentation uses the department's title-cased display name.

## Agents

- Future agent names use a concise responsibility or role name, such as `Architecture` or `Product Director`.
- Future directory identifiers use lowercase kebab-case, such as `architecture` or `product-director`.
- Names describe one primary responsibility.
- Provider names are appropriate only for explicitly platform-specific agents.

## Sub-agents

- Future sub-agent names follow the same lowercase kebab-case directory convention.
- A sub-agent name must be meaningful within its parent scope and must not duplicate the parent's full responsibility.
- Parent relationships must be explicit in future agent definitions rather than inferred only from naming.

## Skills

- Future skill identifiers use lowercase kebab-case and describe a reusable capability, such as `api-contract-review`.
- Skill names must not include a model or CLI provider unless the skill is intentionally provider-specific.
- Skills are not created during Phase 1.

## Workflows

- Future workflow identifiers use lowercase kebab-case and begin with an action-oriented name, such as `review-architecture-change`.
- Workflow names describe an outcome rather than a department or agent identity.
- Workflows are not created during Phase 1.

Documentation filenames use descriptive PascalCase words separated by hyphens, such as `Naming-Conventions.md`.
