# Changelog

## 1.0.0-rc1 — Release Candidate

- Consolidated the frozen organizational, Skill, Workflow, Knowledge, and package architecture.
- Added the local v0.6 Runtime Foundation, Resolution, Context, Execution, UMAL, Invocation, Tool/MCP, and Governance layers.
- Added repository discovery, deterministic Workflow planning/execution, local audit/history, model and Tool selection, Dry Run approval, and CLI diagnostics.
- Added Official Workflow Library Wave 1 and preserved community Skill provenance.
- Added Motion Engineering ACR-001 as a frozen extension.
- Added public documentation, examples, contribution templates, CI validation, and release guidance.

### Breaking changes

The v0.6 runtime is the first executable local runtime and is not compatible with the earlier documentation-only assumption. Frozen metadata contracts require governed phase/ACR changes for incompatibilities.

### Known limitations

State is process-local; Tool/MCP execution is not implemented; OpenAI-compatible and Ollama are the reference invocation adapters; imported community license review remains a release prerequisite.

### Future change process

Changes to frozen architecture require a new approved phase or Architecture Change Request (ACR), with validation and provenance evidence.
