# Implementation Allocation Data Contract Schema (Phase P4.G3)

## 1. Contract Specification

The [`ImplementationAllocationReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/allocation/models.py#L31) is an immutable Pydantic data model (`model_config = ConfigDict(frozen=True)`).

```json
{
  "allocation_id": "alloc-123456",
  "blueprint_id": "blu-987654",
  "workspace_id": "ws-python",
  "workspace_root": "/absolute/path/to/workspace",
  "technology_stack": "python",
  "allocated_targets": [
    {
      "target_id": "tgt-file-0001",
      "target_type": "file",
      "relative_path": "src/main.py",
      "owning_discipline": "Backend",
      "owning_profile_id": "prf-be-eng",
      "owning_profile_role": "Backend Engineer",
      "expected_deliverable": "File Source Implementation: src/main.py",
      "priority": "P1_HIGH",
      "dependencies": []
    }
  ],
  "agent_ownership": {
    "prf-be-eng": ["tgt-file-0001", "tgt-mod-0001"],
    "prf-qa-eng": ["tgt-file-0002"]
  },
  "discipline_ownership": {
    "Backend": ["tgt-file-0001"],
    "Testing": ["tgt-file-0002"]
  },
  "expected_deliverables": [
    "[Backend Engineer] File Source Implementation: src/main.py"
  ],
  "dependencies": {
    "tgt-file-0001": []
  },
  "execution_order": [
    "tgt-file-0001",
    "tgt-file-0002"
  ],
  "coverage": {
    "total_targets": 20,
    "owned_targets": 20,
    "coverage_score": 1.0
  },
  "evidence": {
    "target_count": 20,
    "latency_ms": 1.45,
    "coverage_score": 1.0,
    "validation": {
      "hundred_percent_ownership": true,
      "no_orphan_files": true,
      "no_duplicate_ownership": true,
      "dependency_integrity": true
    }
  },
  "timestamp": "2026-08-06T00:58:00Z",
  "allocation_hash": "e5f6g7h8..."
}
```

---

## 2. Field Definitions

| Field Name | Type | Description |
|---|---|---|
| `allocation_id` | `str` | Unique allocation report identifier (`alloc-xxxxxx`) |
| `blueprint_id` | `str` | Associated blueprint report ID |
| `workspace_id` | `str` | Associated workspace ID |
| `workspace_root` | `str` | Absolute workspace root path string |
| `technology_stack` | `str` | Target technology stack |
| `allocated_targets` | `List[AllocationTarget]` | List of all allocated implementation targets |
| `agent_ownership` | `Dict[str, List[str]]` | Profile ID mapping to assigned target IDs |
| `discipline_ownership` | `Dict[str, List[str]]` | Discipline mapping to assigned target IDs |
| `expected_deliverables` | `List[str]` | Consolidated list of expected deliverables |
| `dependencies` | `Dict[str, List[str]]` | Target dependency DAG mapping target_id to dependency IDs |
| `execution_order` | `List[str]` | Topologically sorted order of target execution |
| `coverage` | `Dict[str, Any]` | Target coverage metrics (100% expected) |
| `evidence` | `Dict[str, Any]` | Validation evidence and latency metrics |
| `timestamp` | `str` | ISO-8601 UTC completion timestamp |
| `allocation_hash` | `str` | SHA-256 hash of allocation payload |
