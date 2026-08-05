# Project Blueprint Data Contract Schema (Phase P4.G2)

## 1. Contract Specification

The [`ProjectBlueprintReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/blueprint/models.py#L31) is an immutable Pydantic data model (`model_config = ConfigDict(frozen=True)`).

```json
{
  "blueprint_id": "blu-123456",
  "workspace_id": "ws-987654",
  "workspace_root": "/absolute/path/to/workspace",
  "technology_stack": "python",
  "project_modules": [
    {
      "module_id": "mod-py-api",
      "name": "Backend API & Controller Layer",
      "discipline": "Backend",
      "relative_path": "src/api",
      "description": "FastAPI / REST API routes and handlers",
      "components": ["RouterHandler", "RequestSchemas", "ServiceController"],
      "dependencies": []
    }
  ],
  "directory_ownership": {
    "src/api": "Backend",
    "src/db": "Database",
    "tests": "Testing",
    "docs": "Documentation"
  },
  "logical_components": [
    {
      "module_id": "mod-py-api",
      "discipline": "Backend",
      "relative_path": "src/api",
      "components": ["RouterHandler", "RequestSchemas"]
    }
  ],
  "engineering_discipline_ownership": {
    "Backend": ["src/api", "module:mod-py-api"],
    "Database": ["src/db", "module:mod-py-db"]
  },
  "technology_stack_mapping": {
    "technology_stack": "python",
    "allocated_module_count": 9,
    "primary_discipline": "Backend",
    "runtime_environment": "Python 3.10+"
  },
  "expected_files": [
    "src/main.py",
    "src/api/routes.py",
    "tests/test_main.py"
  ],
  "expected_deliverables": [
    "Backend Architecture & Source Modules (2 items)",
    "Testing Architecture & Source Modules (1 items)"
  ],
  "dependencies": {
    "mod-py-api": [],
    "mod-py-db": ["mod-py-api"]
  },
  "evidence": {
    "module_count": 9,
    "latency_ms": 1.25,
    "coverage_score": 1.0,
    "validation": {
      "all_modules_owned": true,
      "no_orphan_modules": true,
      "no_duplicate_ownership": true,
      "dependency_integrity": true
    }
  },
  "timestamp": "2026-08-06T00:55:00Z",
  "blueprint_hash": "a1b2c3d4..."
}
```

---

## 2. Field Definitions

| Field Name | Type | Description |
|---|---|---|
| `blueprint_id` | `str` | Unique blueprint identifier (`blu-xxxxxx`) |
| `workspace_id` | `str` | Associated workspace ID |
| `workspace_root` | `str` | Absolute path string of target workspace root |
| `technology_stack` | `str` | Target tech stack (`react`, `nextjs`, `python`, `fastapi`, `flutter`, `monorepo`) |
| `project_modules` | `List[ProjectModule]` | List of allocated project module records |
| `directory_ownership` | `Dict[str, str]` | Mapping from relative directory path to engineering discipline |
| `logical_components` | `List[Dict[str, Any]]` | List of logical software components mapped across modules |
| `engineering_discipline_ownership` | `Dict[str, List[str]]` | Discipline mapping to owned directories and module references |
| `technology_stack_mapping` | `Dict[str, Any]` | Detailed technology stack metadata and primary discipline |
| `expected_files` | `List[str]` | List of expected files to be allocated in P4.G3 |
| `expected_deliverables` | `List[str]` | Expected engineering deliverables per discipline |
| `dependencies` | `Dict[str, List[str]]` | Dependency DAG mapping module ID to dependency IDs |
| `evidence` | `Dict[str, Any]` | Execution evidence, latency metrics, and coverage validation |
| `timestamp` | `str` | ISO-8601 UTC completion timestamp |
| `blueprint_hash` | `str` | SHA-256 hash of blueprint manifest |
