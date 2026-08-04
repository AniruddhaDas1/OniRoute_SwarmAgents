# Release Compliance

## Artifact audit

`pyproject.toml` declares version `1.0.0rc1`, README, MIT license, Python `>=3.12`, runtime dependencies, and the `oniroute = cli.main:app` entry point. A fresh isolated build produced a 95-file wheel and 111-file sdist. The wheel contains the MIT license, correct metadata, and the `oniroute = cli.main:app` console entry point. The sdist contains `LICENSE`, `README.md`, and standard setuptools source-distribution metadata. Neither artifact contains caches, bytecode, Git data, logs, or editor files.

Generated `build/`, `oniroute_swarmagents.egg-info/`, `__pycache__/`, and `.pytest_cache/` paths were removed from the working tree before this audit. Release artifacts must be built from a clean checkout and must not include caches, credentials, editor files, Git data, or development metadata.

## Governance audit

Contribution, Code of Conduct, pull-request, bug, feature, question, support, discussion, security, versioning, release-process, ACR, and freeze documents are present. The stable-release gate remains conditional on a monitored private security contact and resolution of review-required third-party sources.

## Result

**RC packaging: pass for internal validation. Public v1.0.0: blocked.**
