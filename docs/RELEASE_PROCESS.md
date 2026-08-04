# Release Process

Confirm the release scope and freeze boundaries; run the complete tests, `oniroute doctor`, YAML/documentation validation, packaging installation, CLI smoke tests, and `git diff --check`; review licenses, provenance, security, changelog, version, and release notes; create a signed/tagged release from a clean commit; publish artifacts only after reproducibility and installation checks. Never release generated environments or credentials.
