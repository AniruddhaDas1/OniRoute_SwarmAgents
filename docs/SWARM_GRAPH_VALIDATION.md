# Swarm Graph Validation Specification (`docs/SWARM_GRAPH_VALIDATION.md`)

## Executive Summary

This document specifies the structural validation criteria for the **Swarm Graph** in OniRoute (ACR-005 Phase S4).

The Swarm Graph is constructed by `SwarmGraphBuilder` in `runtime.organization.swarm_graph_builder`.

---

## 1. Multi-Perspective Graph Structure

The Swarm Graph integrates five structural views into an immutable graph model (`SwarmGraph`):

```text
                               +-----------------------------+
                               |         SwarmGraph          |
                               +-----------------------------+
                                              |
      +-------------------+-------------------+-------------------+-------------------+
      |                   |                   |                   |                   |
      v                   v                   v                   v                   v
+------------+     +------------+     +------------+     +------------+     +------------+
| Dependency |     | Reporting  |     | Execution  |     | Review     |     | Approval   |
| Graph      |     | Hierarchy  |     | Hierarchy  |     | Hierarchy  |     | Hierarchy  |
+------------+     +------------+     +------------+     +------------+     +------------+
```

---

## 2. Graph Perspective Audits

1. **Dependency Edge View**: Maps data, interface, and blocking contracts between member nodes (`EdgeType.DEPENDENCY`).
2. **Reporting Edge View**: Maps subordinate-to-supervisor reporting lines (`EdgeType.REPORTING`).
3. **Execution Hierarchy View**: Topological level ordering (`level_0`, `level_1`, `level_2`) establishing dependency sequence tiers without execution scheduling.
4. **Review Hierarchy View**: Author-reviewer pairs (`review_pairs`) mapping authors to code reviewers.
5. **Approval Hierarchy View**: Executive and architecture sign-off gates (`approval_gates`).

---

## 3. Structural Validation Rules

- **No Cycles in Dependency Graph**: Inter-member dependencies must form a DAG.
- **Single Supervisory Path**: Subordinate members report to designated leads up to Executive oversight.
- **Node-Member Mapping**: Every node in `SwarmGraph.nodes` must map to an allocated `OrganizationMember`.
