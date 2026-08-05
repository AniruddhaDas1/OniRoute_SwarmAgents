# Repair Plan Schema Specification (Phase P5.E3)

## 1. Schema Specification

The [`RepairPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/healing/models.py#L25) is an immutable Pydantic data model (`model_config = ConfigDict(frozen=True)`).

```json
{
  "plan_id": "rprplan-123456",
  "quality_report_id": "qltr-987654",
  "engineering_result_id": "engres-112233",
  "actions": [
    {
      "action_id": "act-0001",
      "finding_id": "fnd-arch-0001",
      "target_path": "src/main.py",
      "priority": "P1_HIGH",
      "required_changes": "Enforce strict read_only_engine_verified checks during execution.",
      "dependencies": [],
      "execution_order": 1,
      "acceptance_criteria": [
        "Verify finding 'fnd-arch-0001' in 'src/main.py' is fully resolved."
      ]
    }
  ],
  "target_files": [
    "src/main.py"
  ],
  "timestamp": "2026-08-06T01:15:00Z",
  "plan_hash": "b2c3d4e5..."
}
```

---

## 2. Field Definitions

| Field Name | Type | Description |
|---|---|---|
| `plan_id` | `str` | Unique repair plan ID (`rprplan-xxxxxx`) |
| `quality_report_id` | `str` | Associated QualityReport ID |
| `engineering_result_id` | `str` | Associated EngineeringResult ID |
| `actions` | `List[RepairAction]` | Deterministic repair actions |
| `target_files` | `List[str]` | List of target file relative paths |
| `timestamp` | `str` | ISO-8601 UTC creation timestamp |
| `plan_hash` | `str` | SHA-256 hash of repair plan payload |
