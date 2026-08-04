# Final Release Checklist

## Passing checks

- [x] Root Apache License 2.0 and SPDX `Apache-2.0` project metadata are present.
- [x] README, installation, release, versioning, contribution, security, support, discussion, and conduct guidance are present.
- [x] Third-party notices enumerate nine community metadata sources.
- [x] Community and research provenance is preserved; no copied implementation or prompts were found.
- [x] Runtime dependencies and optional build/test dependencies have recorded permissive licenses.
- [x] Entry point, version, README, and license metadata are consistent.
- [x] Fresh wheel/sdist build and content inspection completed.
- [x] `git diff --check` passes for this audit change.

## Release decisions

- [x] AGPL-3.0 `knoxgraeme/skillfish` is catalog/reference metadata only; no AGPL content is imported.
- [x] `multica-ai/andrej-karpathy-skills` is excluded from admission because its license is undetermined.
- [x] Popmotion remains reference-only; no implementation content is reused.
- [ ] Enable GitHub private security advisories before making the repository public.
- [ ] Rebuild wheel and sdist from the final release commit and archive their manifests and hashes with the GitHub release.

## Recommendation

Phase 7.5 performs final validation. Repository publication must enable the private security advisory channel and use artifacts rebuilt from the final commit.
