# Developer Guide

Install editable dependencies and run `python -m pytest -q`. Follow `AGENTS.md`, preserve frozen layers, prefer small conventional commits, and keep provider logic inside adapters. Add tests for success, failure, CLI behavior, and governance. Use Pydantic for contracts, PyYAML for metadata, NetworkX for relationships, Typer/Rich for CLI output, and standard-library HTTP at adapter boundaries. Run `git diff --check` before committing.
