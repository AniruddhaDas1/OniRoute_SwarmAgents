# Final Release Checklist

## Passing checks

- [x] Root MIT license and SPDX-compatible `MIT` project metadata are present.
- [x] README, installation, release, versioning, contribution, security, support, discussion, and conduct guidance are present.
- [x] Third-party notices enumerate nine community metadata sources.
- [x] Community and research provenance is preserved; no copied implementation or prompts were found.
- [x] Runtime dependencies and optional build/test dependencies have recorded permissive licenses.
- [x] Entry point, version, README, and license metadata are consistent.
- [x] Fresh wheel/sdist build and content inspection completed.
- [x] `git diff --check` passes for this audit change.

## Blocking before v1.0.0

- [ ] Decide whether AGPL-3.0 `knoxgraeme/skillfish` remains catalog-only or can be distributed under a documented legal policy.
- [ ] Confirm the license for `multica-ai/andrej-karpathy-skills` or exclude the source from release references.
- [ ] Confirm Popmotion's license before any reuse; keep it reference-only until then.
- [ ] Enable GitHub private security advisories or publish a monitored maintainer security contact.
- [ ] Rebuild wheel and sdist from the final clean release commit and archive their manifests and hashes with the release.

## Recommendation

Proceed to Phase 7.5 Final Release Validation only after the blocking items are resolved or explicitly accepted by maintainers. Do not publish a stable v1.0.0 artifact while any blocking item remains unchecked.
