"""Canonical engineering organization roles for OniRoute Organization Builder (ACR-005 Phase S1).

Defines canonical and extensible role types and role definitions for AI engineering swarms.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OrganizationRoleType(str, Enum):
    """Canonical engineering roles for swarm organizations."""

    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    SECURITY = "security"
    QA = "qa"
    DEVOPS = "devops"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    REVIEWER = "reviewer"
    RESEARCH = "research"
    MOBILE = "mobile"
    AI = "ai"
    INFRASTRUCTURE = "infrastructure"
    CUSTOM = "custom"


class OrganizationRole(BaseModel):
    """Immutable role definition within the engineering organization."""

    role_id: str = Field(..., description="Unique role identifier (e.g. role-backend-lead)")
    role_type: OrganizationRoleType | str = Field(
        ..., description="Canonical or extensible role type designation"
    )
    title: str = Field(..., description="Human-readable title (e.g. Senior Backend Engineer)")
    description: str = Field(..., description="Detailed role scope and purpose")
    primary_responsibility: str = Field(..., description="Single primary engineering responsibility")
    inputs: list[str] = Field(default_factory=list, description="Declarative input artifacts/contracts")
    outputs: list[str] = Field(default_factory=list, description="Declarative output deliverables/artifacts")
    boundaries: list[str] = Field(default_factory=list, description="Explicit domain boundaries and constraints")
    allowed_capabilities: list[str] = Field(
        default_factory=list, description="List of capability IDs this role is authorized to perform"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible metadata attributes")
