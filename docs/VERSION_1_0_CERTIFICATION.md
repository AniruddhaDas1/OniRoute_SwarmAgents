# Version 1.0 Certification Evidence

This document records the final commands, environment, counts, artifact manifests, and results used to certify OniRoute v1.0.0. Evidence reflects the final stable release tree before tagging.

## Required gates

- Repository load and validation
- Complete pytest suite
- All YAML parsing
- Public CLI help and safe smoke commands
- Documentation links and whitespace
- Apache-2.0/version consistency
- Community metadata boundary
- Wheel and source distribution contents

The final observed results are recorded in this file before the certification commit.

## Observed results

Environment: Python 3.14.6, Darwin 25.5.0 arm64.
Tests: 34 passed, 0 failed, 0 skipped; 30.85 seconds.
Repository validation: PASS; 31 Agents, 265 Sub-Agents, 1,087 Skills, 20 Workflows; zero errors, warnings, or duplicates.
YAML parsing: 1,436 files parsed successfully.
CLI: 55 help paths passed; 41 safe smoke commands passed; 45 leaf commands are registered. `invoke` was help-validated because it requires an external model endpoint.
Documentation: 6,560 Markdown files checked across the repository; zero broken relative links; `git diff --check` passed.
License consistency: root Apache-2.0, 96 Official Skills Apache-2.0, 20 Official Workflows Apache-2.0, 991 Community license declarations preserved as upstream metadata.

## Package artifacts

| Artifact | Files | SHA-256 |
|---|---:|---|
| `oniroute_swarmagents-1.0.0-py3-none-any.whl` | 99 | `9332026d4770f32bb6af422cd2f937e62b1b3ef82c2d3aa896a86b2151e5d0a4` |
| `oniroute_swarmagents-1.0.0.tar.gz` | 113 | `3bc611e089202b5cc0fa35ea13de4d9b6319fbe4a506e24214b835502ce98f15` |

Both artifacts contain README, LICENSE, NOTICE, AUTHORS, Apache-2.0 package metadata, and the `oniroute = cli.main:app` entry point. No cache, bytecode, Git, editor, or temporary files were found in either artifact.
