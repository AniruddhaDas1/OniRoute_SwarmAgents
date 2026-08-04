# Knowledge Source Specification

A canonical Knowledge Source record should contain:

- **Source ID** — stable, unique identifier.
- **Display Name** — human-readable name.
- **Description** — purpose and scope of the origin.
- **Origin** — URI, repository locator, local reference, or connector reference.
- **License** — declared source license and attribution requirements.
- **Trust Level** — Official, Verified, Community, Enterprise, Personal, Experimental, or Unknown.
- **Owner** — accountable person, organization, or team.
- **Revision** — branch, tag, commit, digest, or source revision.
- **Capabilities** — discovery, versioning, change detection, asset indexing, or other declared capabilities.
- **Discovery Status** — current state and most recent discovery result.
- **Supported Asset Types** — Skills, Templates, Prompts, Documentation, or future asset classes.
- **Authentication** — conceptual requirement and credential policy reference; never secret material.

Records should also retain discovery timestamps, validation evidence, provenance references, refresh policy, and disable/deprecation rationale.
