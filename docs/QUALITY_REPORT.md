# Quality Report Schema Specification (Phase P5.E2)

## 1. Schema Specification

The [`QualityReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/review/models.py#L31) is an immutable Pydantic data model (`model_config = ConfigDict(frozen=True)`).

```json
{
  "report_id": "qltr-123456",
  "engineering_result_id": "engres-987654",
  "contract_id": "ctr-0001",
  "reviewer_profiles": [
    "prf-devops-eng",
    "prf-doc-spec",
    "prf-lead-arch",
    "prf-qa-eng",
    "prf-sec-auditor"
  ],
  "findings": [
    {
      "finding_id": "fnd-arch-info",
      "category": "Architecture",
      "severity": "INFO",
      "reviewer_profile_id": "prf-lead-arch",
      "reviewer_role": "Lead System Architect",
      "description": "Architecture and modular boundaries satisfy system standards.",
      "target_path": "src/main.py",
      "recommended_fix": "Maintain existing modular boundaries."
    }
  ],
  "architecture_score": 1.0,
  "security_score": 1.0,
  "performance_score": 1.0,
  "testing_score": 1.0,
  "documentation_score": 1.0,
  "contract_compliance": true,
  "approval_status": "APPROVED",
  "required_fixes": [],
  "evidence": {
    "engineering_result_id": "engres-987654",
    "finding_count": 5,
    "latency_ms": 1.25,
    "zero_workspace_write": true
  },
  "timestamp": "2026-08-06T01:12:00Z",
  "report_hash": "a1b2c3d4..."
}
```

---

## 2. Field Definitions

| Field Name | Type | Description |
|---|---|---|
| `report_id` | `str` | Unique quality report ID (`qltr-xxxxxx`) |
| `engineering_result_id` | `str` | Associated engineering result ID |
| `contract_id` | `str` | Associated engineering contract ID |
| `reviewer_profiles` | `List[str]` | List of assigned reviewer profile IDs |
| `findings` | `List[QualityFinding]` | Structured review findings |
| `architecture_score` | `float` | Architecture score (0.0 to 1.0) |
| `security_score` | `float` | Security score (0.0 to 1.0) |
| `performance_score` | `float` | Performance score (0.0 to 1.0) |
| `testing_score` | `float` | Testing score (0.0 to 1.0) |
| `documentation_score` | `float` | Documentation score (0.0 to 1.0) |
| `contract_compliance` | `bool` | True if contract compliance pass rate is 100% |
| `approval_status` | `str` | Approval status (`APPROVED`, `CONDITIONALLY_APPROVED`, `REJECTED`) |
| `required_fixes` | `List[str]` | List of required fixes for Self-Healing (P5.E3) |
| `evidence` | `Dict[str, Any]` | Validation evidence and audit logs |
| `timestamp` | `str` | ISO-8601 UTC completion timestamp |
| `report_hash` | `str` | SHA-256 hash of quality report payload |
