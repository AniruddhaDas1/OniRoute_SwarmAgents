# Swarm Graph Architecture (`docs/SWARM_GRAPH.md`)

## Executive Summary

The **Swarm Graph** is the multi-perspective directed graph representation of an AI engineering organization swarm. It captures technical dependencies, reporting structures, execution sequencing tiers, code review assignments, and governance approval gates.

Under ACR-005 Phase S1, the Swarm Graph is strictly an **ARCHITECTURE ONLY** model. It contains **NO** task scheduler, **NO** dynamic event dispatchers, and **NO** execution runtime logic.

---

## 1. Multi-Perspective Graph Structure

The Swarm Graph (`runtime.organization.swarm_graph.SwarmGraph`) integrates five distinct structural perspectives:

```text
                               +-----------------------------+
                               |         SwarmGraph          |
                               +-----------------------------+
                                              |
      +-------------------+-------------------+-------------------+-------------------+
      |                   |                   |                   |                   |
      v                   v                   v                   v                   v
+------------+     +------------+     +------------+     +------------+     +------------+
| Directed   |     | Reporting  |     | Execution  |     | Review     |     | Approval   |
| Dependency |     | Hierarchy  |     | Hierarchy  |     | Hierarchy  |     | Hierarchy  |
| Graph      |     |            |     |            |     |            |     |            |
+------------+     +------------+     +------------+     +------------+     +------------+
```

---

## 2. Core Graph Components

### `SwarmGraphNode`
Represents an individual node in the swarm graph, mapped to an `OrganizationMember` and `OrganizationRole`.

```python
class SwarmGraphNode(BaseModel):
    node_id: str
    member_id: str
    role_id: str
    domain: str
    metadata: dict[str, Any] = {}
```

### `SwarmGraphEdge`
Represents a directed link between nodes in the swarm graph.

```python
class EdgeType(str, Enum):
    DEPENDENCY = "dependency"
    REPORTING = "reporting"
    EXECUTION = "execution"
    REVIEW = "review"
    APPROVAL = "approval"

class SwarmGraphEdge(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType = EdgeType.DEPENDENCY
    weight: float = 1.0
    metadata: dict[str, Any] = {}
```

---

## 3. Five Structural Perspectives

### 1. Directed Dependency Graph
Defines data, interface, and blocking relationships between engineering disciplines. For example, Database schema contracts must precede Backend API implementations, which in turn precede Frontend UI integration.

### 2. Reporting Hierarchy (`ReportingHierarchy`)
Captures structural reporting lines across departments:
```text
Executive Department
  └── Engineering Department
        ├── Architecture Lead
        │     ├── Backend Lead
        │     └── Frontend Lead
        └── Platform Department
```

### 3. Execution Hierarchy (`ExecutionHierarchy`)
Captures topological dependency ordering levels (`execution_levels`). Member slots in Level 0 (e.g. Architecture, Database) produce foundational contracts before Level 1 member slots (Backend, Frontend) consume them.

### 4. Review Hierarchy (`ReviewHierarchy`)
Defines mandatory peer review and supervisory verification pairs (`review_pairs`), ensuring every generated artifact is audited by a designated `REVIEWER` or discipline lead before acceptance.

### 5. Approval Hierarchy (`ApprovalHierarchy`)
Establishes governance sign-off gates (`approval_gates`) for security clearance, budget checks, human-in-the-loop approvals, and executive sign-off.

---

## 4. Swarm Graph Schema

```python
class SwarmGraph(BaseModel):
    graph_id: str
    mission_id: str
    organization_id: str
    nodes: list[SwarmGraphNode] = []
    edges: list[SwarmGraphEdge] = []
    reporting_hierarchy: ReportingHierarchy = Field(default_factory=ReportingHierarchy)
    execution_hierarchy: ExecutionHierarchy = Field(default_factory=ExecutionHierarchy)
    review_hierarchy: ReviewHierarchy = Field(default_factory=ReviewHierarchy)
    approval_hierarchy: ApprovalHierarchy = Field(default_factory=ApprovalHierarchy)
    metadata: dict[str, Any] = {}
```

---

## 5. Architectural Boundaries

- **No Scheduler**: Does not include thread pools, asyncio event loops, or queue dispatchers.
- **No Agent Execution**: Nodes and edges describe organizational topology, not runtime execution state.
- **No AI Invocation**: Graph construction is strictly declarative topology modeling.
