# OniRoute Packages

## Purpose

A Package is the deployment and distribution unit for reusable OniRoute capabilities. It may group Skills, future Workflow definitions, prompt templates, documentation, knowledge references, adapter definitions, configuration, examples, tests, assets, and metadata.

Packages are not Agents and do not own responsibilities. Packages are not Skills; they may contain or reference Skills. Package architecture does not imply installation or execution.

## Relationships

- Knowledge Sources identify origins from which Packages may be discovered.
- Skills are bounded capabilities contained or referenced by Packages.
- Agents may be declared compatible consumers without being modified by a Package.
- Workflows may later be packaged as definitions, but none are created here.
- Registry metadata supports discovery, versions, trust, and validation.
- Community Catalog supplies metadata-only candidate origins.
- Runtime may later install or consume approved Packages; this phase defines no Runtime behavior.

The specification directory defines the universal Package contract. No actual Packages are created.

