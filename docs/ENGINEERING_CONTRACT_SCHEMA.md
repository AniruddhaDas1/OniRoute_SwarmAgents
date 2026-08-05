# Engineering Contract Data Contract Schema (Phase P4.G4)

## 1. Contract Specification

The [`EngineeringContractReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/contracts/models.py#L35) is an immutable Pydantic data model (`model_config = ConfigDict(frozen=True)`).

```json
{
  "report_id": "ctrr-123456",
  "allocation_id": "alloc-987654",
  "workspace_id": "ws-python",
  "workspace_root": "/absolute/path/to/workspace",
  "technology_stack": "python",
  "contracts": [
    {
      "contract_id": "ctr-0001",
      "target_path": "src/main.py",
      "target_type": "file",
      "assigned_profile_id": "prf-be-eng",
      "assigned_profile_role": "Backend Engineer",
      "engineering_discipline": "Backend",
      "input_dependencies": [],
      "output_artifacts": ["src/main.py"],
      "interface_constraints": {
        "target_type": "file",
        "exported_symbols": ["main", "handler"],
        "api_protocol": "REST/JSON"
      },
      "architecture_constraints": [
        "Preserve clear boundaries between specs and code.",
        "Assert read-only Engine Root safety boundaries strictly."
      ],
      "coding_standards": [
        "Use Python 3.10+ type annotations.",
        "Follow PEP8 with 100-character line length limit."
      ],
      "naming_rules": [
        "Use PascalCase for classes and snake_case for functions."
      ],
      "security_requirements": [
        "Sanitize inputs using Pydantic models.",
        "Do NOT embed hardcoded secrets."
      ],
      "performance_expectations": {
        "max_latency_ms": 100.0,
        "memory_limit_mb": 512
      },
      "testing_requirements": [
        "Write automated unit tests covering key branches."
      ],
      "documentation_requirements": [
        "Include professional docstrings."
      ],
      "acceptance_criteria": [
        "Target path 'src/main.py' satisfies Backend requirements."
      ],
      "review_requirements": [
        "Requires peer review approval from Lead System Architect."
      ],
      "generation_priority": "P1_HIGH",
      "execution_wave": 3,
      "contract_hash": "a1b2c3d4..."
    }
  ],
  "agent_contracts": {
    "prf-be-eng": ["ctr-0001"]
  },
  "discipline_contracts": {
    "Backend": ["ctr-0001"]
  },
  "expected_outputs": [
    "src/main.py"
  ],
  "execution_waves": {
    "3": ["ctr-0001"]
  },
  "evidence": {
    "contract_count": 20,
    "latency_ms": 1.85,
    "coverage_score": 1.0,
    "validation": {
      "hundred_percent_allocation_coverage": true,
      "no_orphan_contracts": true,
      "no_duplicate_contracts": true,
      "dependency_integrity": true,
      "constraint_completeness": true,
      "acceptance_completeness": true
    }
  },
  "timestamp": "2026-08-06T01:00:00Z",
  "report_hash": "f9e8d7c6..."
}
```

---

## 2. Field Definitions

| Field Name | Type | Description |
|---|---|---|
| `report_id` | `str` | Unique report identifier (`ctrr-xxxxxx`) |
| `allocation_id` | `str` | Associated allocation report ID |
| `workspace_id` | `str` | Associated workspace ID |
| `workspace_root` | `str` | Absolute path string of workspace root |
| `technology_stack` | `str` | Target technology stack |
| `contracts` | `List[EngineeringContract]` | List of generated engineering contract specs |
| `agent_contracts` | `Dict[str, List[str]]` | Profile ID mapping to contract IDs |
| `discipline_contracts` | `Dict[str, List[str]]` | Discipline mapping to contract IDs |
| `expected_outputs` | `List[str]` | Consolidated list of expected output artifact paths |
| `execution_waves` | `Dict[int, List[str]]` | Execution wave mapping (1 to 6) |
| `evidence` | `Dict[str, Any]` | Validation evidence and latency metrics |
| `timestamp` | `str` | ISO-8601 UTC completion timestamp |
| `report_hash` | `str` | SHA-256 hash of report payload |
