# Runtime Production Checklist

- [x] All runtime tests pass.
- [x] Repository and frozen metadata load without mutation.
- [x] Resolution graph has unique nodes.
- [x] Context objects and routing plans build successfully.
- [x] Workflow planning and deterministic execution succeed.
- [x] AI Dry Run and mock invocation paths succeed.
- [x] AI invocation passes through UMAL and governance.
- [x] Tool recommendation passes through governance.
- [x] Budgets and immutable audit records are local.
- [x] CLI help, exit codes, inspection, planning, execution, catalog, and governance commands work.
- [x] Configuration YAML parses.
- [x] No telemetry, analytics, mandatory cloud, hidden persistence, or secrets are present.
- [x] No runtime mutation of frozen architecture occurs.
- [x] `git diff --check` passes.

Production deployments must explicitly configure real model endpoints, approval defaults, permission policy, budgets, and security rules before enabling Automatic AI invocation.
