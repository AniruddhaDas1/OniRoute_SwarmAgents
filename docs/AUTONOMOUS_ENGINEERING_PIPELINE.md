# Autonomous Engineering Pipeline Specification (Phase P5)

## 1. Pipeline Architectural Principles

1. **Immutable Contracts**: Every stage consumes only immutable upstream contracts (`model_config = ConfigDict(frozen=True)`).
2. **Strict Scoping**: Code generation and self-healing operate **ONLY** on target paths allocated in `EngineeringContractReport` or `RepairPlan`.
3. **Engine Root Read-Only Safety**: Any write attempt into engine root files (`runtime/`, `cli/`) raises a boundary violation error.
4. **Independent Reviewer Profiles**: Cross-agent review assigns 5 independent reviewer agent roles (`prf-lead-arch`, `prf-sec-auditor`, `prf-devops-eng`, `prf-qa-eng`, `prf-doc-spec`).
5. **Traceability**: SHA-256 hashes linked across all contracts from `EngineeringResult` to `EngineeringCertificationReport`.
