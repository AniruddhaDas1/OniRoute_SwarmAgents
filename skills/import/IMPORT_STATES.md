# Import States

An import operation progresses through these states:

- **Discovered** — source identified and classified.
- **Queued** — accepted for controlled processing.
- **Importing** — evidence and package metadata are being inspected.
- **Normalized** — source information is mapped to the OniRoute specification.
- **Validated** — required checks passed.
- **Installed** — approved package is present in the local Skill store.
- **Rejected** — policy or validation prevents admission.
- **Failed** — processing could not complete due to an operational or integrity error.
- **Archived** — historical import record retained but no longer active.

Valid progress is `Discovered → Queued → Importing → Normalized → Validated → Installed`. `Rejected` and `Failed` are terminal for the attempt; `Archived` may follow any retained terminal record. Retry creates a new attempt linked to the prior manifest.
