## Summary

<!-- Briefly describe what this pull request does and why. -->

## Scope and affected layer

<!-- Which top-level directory or concern does this change touch (e.g., docs/, runtime/, cli/, config/, agents/)? -->

## Validation

- [ ] `python -m pytest -q` passes
- [ ] `oniroute doctor` passes (when relevant to repository loading)
- [ ] `yaml.safe_load` succeeds on changed YAML files
- [ ] Markdown links and whitespace validate
- [ ] `git diff --check` passes

## Compatibility and security

<!-- Does this change affect frozen architecture, public interfaces, or governance boundaries? Link to an approved ACR/phase if one is required. -->

- [ ] Frozen layers are unchanged, or the approved ACR/phase is linked.
- [ ] No secrets, credentials, generated environments, provider-specific coupling, or unrelated changes are included.

## Documentation

- [ ] Documentation is updated to reflect the change.
- [ ] New or modified documentation renders correctly and internal links resolve.
