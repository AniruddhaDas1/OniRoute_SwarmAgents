"""Deterministic Swarm Graph Builder for OniRoute Organization Builder (ACR-005 Phase S4).

Constructs canonical multi-perspective Swarm Graphs from an Organization topology:
- Nodes (Departments, Members, Roles, Domains)
- Edges (Dependencies, Reporting, Execution tiers, Review chains, Approval gates)
- Reporting Hierarchy, Execution Hierarchy, Review Hierarchy, and Approval Hierarchy views

Contains NO task scheduler, event dispatchers, or execution runtime loops.
"""

from __future__ import annotations

from typing import Any

from .contracts import SwarmGraphBuilderContract
from .models import Organization
from .swarm_graph import (
    ApprovalHierarchy,
    EdgeType,
    ExecutionHierarchy,
    ReportingHierarchy,
    ReviewHierarchy,
    SwarmGraph,
    SwarmGraphEdge,
    SwarmGraphNode,
)


class SwarmGraphBuilder(SwarmGraphBuilderContract):
    """Deterministic Swarm Graph Builder engine."""

    def build_swarm_graph(self, organization: Organization) -> SwarmGraph:
        """Construct multi-perspective Swarm Graph from an Organization."""
        mission_id = organization.mission_id
        org_id = organization.organization_id
        graph_id = f"sg-{org_id}"

        # 1. Build Nodes
        nodes: list[SwarmGraphNode] = []
        member_node_map: dict[str, str] = {}

        for member in organization.members:
            node_id = f"node-{member.member_id}"
            member_node_map[member.member_id] = node_id
            domain = member.role.role_type if isinstance(member.role.role_type, str) else member.role.role_type.value
            node = SwarmGraphNode(
                node_id=node_id,
                member_id=member.member_id,
                role_id=member.role.role_id,
                domain=domain,
                metadata={"title": member.role.title, "capabilities": member.capability_ids},
            )
            nodes.append(node)

        # 2. Build Edges
        edges: list[SwarmGraphEdge] = []

        # Dependency edges from organization.dependencies
        edge_counter = 1
        for dep in organization.dependencies:
            src_node = member_node_map.get(dep.source_member_id)
            tgt_node = member_node_map.get(dep.target_member_id)
            if src_node and tgt_node:
                edge = SwarmGraphEdge(
                    edge_id=f"e-dep-{edge_counter:03d}",
                    source_node_id=src_node,
                    target_node_id=tgt_node,
                    edge_type=EdgeType.DEPENDENCY,
                    metadata={"description": dep.description, "dependency_type": dep.dependency_type.value},
                )
                edges.append(edge)
                edge_counter += 1

        # Reporting edges from organization.hierarchy
        rep_pairs: list[dict[str, str]] = []
        for pair in organization.hierarchy.reporting_relationships:
            sub = pair.get("subordinate_id") or pair.get("subordinate")
            sup = pair.get("supervisor_id") or pair.get("supervisor")
            if sub and sup:
                rep_pairs.append({"subordinate_id": str(sub), "supervisor_id": str(sup)})
                src_node = member_node_map.get(str(sub))
                tgt_node = member_node_map.get(str(sup))
                if src_node and tgt_node:
                    edge = SwarmGraphEdge(
                        edge_id=f"e-rep-{edge_counter:03d}",
                        source_node_id=src_node,
                        target_node_id=tgt_node,
                        edge_type=EdgeType.REPORTING,
                    )
                    edges.append(edge)
                    edge_counter += 1

        # 3. Execution Hierarchy (Topological Level Tiers)
        level_0 = [m.member_id for m in organization.members if m.role.role_type in ("architecture", "executive_director", "custom")]
        level_1 = [m.member_id for m in organization.members if m.role.role_type in ("database", "backend", "security")]
        level_2 = [m.member_id for m in organization.members if m.role.role_type in ("frontend", "qa", "devops", "documentation")]
        execution_levels = [lvl for lvl in [level_0, level_1, level_2] if lvl]

        # 4. Review Hierarchy (Review pairs)
        review_pairs: list[dict[str, str]] = []
        arch_member = next((m.member_id for m in organization.members if m.role.role_type == "architecture"), None)
        reviewer_member = next((m.member_id for m in organization.members if m.role.role_type == "reviewer"), arch_member)

        for member in organization.members:
            if reviewer_member and member.member_id != reviewer_member:
                review_pairs.append({"author_member_id": member.member_id, "reviewer_member_id": reviewer_member})
                src_node = member_node_map.get(member.member_id)
                tgt_node = member_node_map.get(reviewer_member)
                if src_node and tgt_node:
                    edge = SwarmGraphEdge(
                        edge_id=f"e-rev-{edge_counter:03d}",
                        source_node_id=src_node,
                        target_node_id=tgt_node,
                        edge_type=EdgeType.REVIEW,
                    )
                    edges.append(edge)
                    edge_counter += 1

        # 5. Approval Hierarchy (Approval Gates)
        exec_member = next((m.member_id for m in organization.members if "executive" in m.member_id or m.role.role_type == "custom"), "mem-executive-01")
        approval_gates: list[dict[str, Any]] = [
            {
                "gate_id": "gate-architecture-signoff",
                "gate_name": "Architecture Sign-off Gate",
                "approver_member_id": arch_member or exec_member,
            },
            {
                "gate_id": "gate-executive-governance",
                "gate_name": "Executive Governance Gate",
                "approver_member_id": exec_member,
            },
        ]

        return SwarmGraph(
            graph_id=graph_id,
            mission_id=mission_id,
            organization_id=org_id,
            nodes=nodes,
            edges=edges,
            reporting_hierarchy=ReportingHierarchy(supervisor_subordinate_pairs=rep_pairs),
            execution_hierarchy=ExecutionHierarchy(execution_levels=execution_levels),
            review_hierarchy=ReviewHierarchy(review_pairs=review_pairs),
            approval_hierarchy=ApprovalHierarchy(approval_gates=approval_gates),
            metadata={"total_nodes": len(nodes), "total_edges": len(edges)},
        )
