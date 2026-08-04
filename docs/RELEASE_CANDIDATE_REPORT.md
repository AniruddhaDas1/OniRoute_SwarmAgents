# Release Candidate Report

## Candidate

`1.0.0rc1` / `v1.0.0-rc1`

## Validation

- Repository and `oniroute doctor`: PASS.
- Runtime test suite: PASS, 28 tests.
- YAML validation: PASS for repository YAML.
- Markdown link audit: PASS, zero missing local targets.
- Example shell syntax: PASS.
- Standards-compliant source distribution and wheel build: PASS using `python -m build`.
- Clean-install simulation: PASS in an isolated virtual environment with editable package installation and CLI startup.
- `git diff --check`: PASS.

## Packaging

The wheel builds as `oniroute_swarmagents-1.0.0rc1-py3-none-any.whl` and contains 95 expected runtime, CLI, license, entry-point, and distribution-metadata files. It contains no caches, editor files, Git data, temporary content, or development egg-info. The sdist builds as `oniroute_swarmagents-1.0.0rc1.tar.gz`; its setuptools-generated `.egg-info` directory is standard required source-distribution metadata. Package discovery is explicitly limited to runtime subpackages and CLI.

## Documentation and repository health

README, installation, quick start, CLI, architecture, developer, contribution, FAQ, troubleshooting, security, release, versioning, examples, templates, website copy, GitHub community templates, CI validation, and repository health documentation are present. Frozen runtime, agents, skills, workflows, schemas, and architecture were not changed.

## Performance baseline

Cold repository load: 5.44 s; graph build: 84.6 ms; Context creation: 84.2 ms; Workflow planning: 208.8 ms; peak traced memory: 28.6 MB. These are documented baselines, not release SLOs.

## Readiness decision

**Release Candidate: YES for internal validation and packaging review. Public v1.0: NOT YET READY.** The remaining blocker is third-party licensing/attribution review for the AGPL-3.0 Skillfish import and the source marked License review required. No GitHub tag or release was created.
