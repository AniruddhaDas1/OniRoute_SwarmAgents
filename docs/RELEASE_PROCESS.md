# Release Process

Confirm the release scope and freeze boundaries; install release tooling with `python -m pip install -e '.[dev]'`; run the complete tests, `oniroute doctor`, YAML/documentation validation, CLI smoke tests, `python -m build`, and `git diff --check`; review wheel/sdist contents, licenses, provenance, security, changelog, version, and release notes; create a signed/tagged release from a clean commit; publish artifacts only after reproducibility and installation checks. Never release generated environments or credentials.
