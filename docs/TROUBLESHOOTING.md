# Troubleshooting

- `ModuleNotFoundError`: activate the virtual environment and reinstall with `python -m pip install -e .`.
- `doctor` fails: inspect the reported YAML path, duplicate ID, missing metadata, or broken reference.
- Model not found: check `config/models.yaml` IDs and aliases.
- Invocation denied: review `config/policies.yaml`, approvals, budgets, model allowlists, and permissions.
- Connection refused: confirm the configured local endpoint is running; Dry Run does not require it.
- Empty history/audit in a new CLI process: these stores are intentionally in-memory.
