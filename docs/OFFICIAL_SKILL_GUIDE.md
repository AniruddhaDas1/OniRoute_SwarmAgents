# Official OniRoute Skill Guide

## Official Skill Philosophy

Official Skills are original, provider-independent decision guides maintained by OniRoute. They synthesize durable engineering principles without copying community wording, prompts, examples, or repository structures. They support accountable Agents but do not replace Agent ownership or provide runtime execution.

## Writing Standards

- State one bounded purpose and problem.
- Use explicit outcomes, constraints, trade-offs, and failure conditions.
- Separate universal principles from frameworks, vendors, and implementation code.
- Include decision guidance rather than exhaustive checklists.
- Use consistent OniRoute terminology for Agents, sub-agents, Skills, context, validation, lifecycle, and trust.
- Cite research sources in `references.md` without reproducing source content.

## Naming Standards

- Canonical IDs use `official.<domain>.<skill-name>`.
- Directories and Skill names use lowercase hyphen-case.
- Display names are concise capability names.
- “Fundamentals” is reserved for cross-domain foundations; domain Skills use the direct capability name.

## Ownership

Every Official Skill has exactly one Primary Owner Agent and one Primary Owner Sub-Agent. Secondary and consumer mappings support collaboration and do not transfer ownership. Overlapping topics must be separated by responsibility, such as universal Authentication Fundamentals versus future provider-specific authentication guidance.

## Review Process

1. Confirm original authorship and research attribution.
2. Validate schema, required files, and mandatory sections.
3. Review responsibility boundaries and duplicate concepts.
4. Verify provider independence and absence of implementation code.
5. Validate Agent and sub-agent identities.
6. Review security, compatibility, quality, and learning-resource claims.
7. Record approval and version history.

## Promotion Process

Candidates move to Official only after ownership, validation, trust, quality, provenance, and compatibility review. Official status requires version `1.0.0` or later, quality score 100 for initial canonical releases, verified validation, and maintained OniRoute ownership.

## Deprecation Policy

Deprecated Skills remain discoverable with reason, successor, migration guidance, and final compatible version. Deprecation never erases provenance or version history. Removal requires an architecture decision and retained audit evidence.

## Contribution Guidelines

Contributions must be original, narrowly scoped, provider-independent, and mapped to one primary owner. Community sources may inform research, but contributors must not copy wording, examples, prompts, or proprietary structures. New Skills require duplicate analysis and must demonstrate a capability gap not already covered by the Official catalog.
