"""Immutable Swarm Graph models for OniRoute Organization Builder (ACR-005 Phase S1).

Defines directed dependency graphs, reporting hierarchies, execution hierarchies,
review hierarchies, and approval hierarchies without scheduler logic or execution loops.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EdgeType(str, Enum):
    """Types of graph relationship edges in Swarm Graph."""

    DEPENDENCY = "dependency"
    REPORTING = "reporting"
    EXECUTION = "execution"
    REVIEW = "review"
    APPROVAL = "approval"


class SwarmGraphNode(BaseModel):
    """Node in the Swarm Graph representing a member or role."""

    node_id: str = Field(..., description="Unique node identifier (e.g. node-backend-lead)")
    member_id: str = Field(..., description="Associated organization member ID")
    role_id: str = Field(..., description="Associated role ID")
    domain: str = Field(..., description="Engineering domain category")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible node metadata")


class SwarmGraphEdge(BaseModel):
    """Directed edge in the Swarm Graph."""

    edge_id: str = Field(..., description="Unique edge identifier")
    source_node_id: str = Field(..., description="Source node ID (upstream / supervisor / caller)")
    target_node_id: str = Field(..., description="Target node ID (downstream / subordinate / callee)")
    edge_type: EdgeType = Field(default=EdgeType.DEPENDENCY, description="Type of graph edge")
    weight: float = Field(default=1.0, description="Graph edge weight")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible edge metadata")


class ReportingHierarchy(BaseModel):
    """Directed reporting relationships graph structure."""

    supervisor_subordinate_pairs: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of dicts mapping 'supervisor_id' to 'subordinate_id'",
    )

    def is_valid(self) -> bool:
        """Validate structure presence without runtime behavior."""
        return True


class ExecutionHierarchy(BaseModel):
    """Declarative order of execution hierarchy levels."""

    execution_levels: list[list[str]] = Field(
        default_factory=list,
        description="Layered lists of member_ids ordered by topological dependency tier",
    )


class ReviewHierarchy(BaseModel):
    """Peer and supervisory code/design review graph structure."""

    review_pairs: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of dicts mapping 'author_member_id' to 'reviewer_member_id'",
    )


class ApprovalHierarchy(BaseModel):
    """Governance and executive sign-off hierarchy structure."""

    approval_gates: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of approval gate definitions mapping member_ids to mandatory approvers",
    )


class SwarmGraph(BaseModel):
    """Canonical Swarm Graph encapsulating all directed graph perspectives."""

    graph_id: str = Field(..., description="Unique Swarm Graph identifier")
    mission_id: str = Field(..., description="Associated mission identifier")
    organization_id: str = Field(..., description="Associated organization identifier")
    nodes: list[SwarmGraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: list[SwarmGraphEdge] = Field(default_factory=list, description="Directed relationship edges")
    reporting_hierarchy: ReportingHierarchy = Field(
        default_factory=ReportingHierarchy, description="Reporting hierarchy structure"
    )
    execution_hierarchy: ExecutionHierarchy = Field(
        default_factory=ExecutionHierarchy, description="Execution hierarchy structure"
    )
    review_hierarchy: ReviewHierarchy = Field(
        default_factory=ReviewHierarchy, description="Review hierarchy structure"
    )
    approval_hierarchy: ApprovalHierarchy = Field(
        default_factory=ApprovalHierarchy, description="Approval hierarchy structure"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Graph metadata")
