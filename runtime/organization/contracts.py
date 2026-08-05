"""Interface contracts for OniRoute Organization Builder (ACR-005 Phase S1).

Defines ABC interfaces for the canonical Organization Builder pipeline components.
All interfaces are architecture-only specifications and do not contain runtime execution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from runtime.mission.models import ExecutionRequest

from .blueprint import ExecutionBlueprint
from .capability import CapabilityReport
from .models import Organization, OrganizationReport
from .swarm_graph import SwarmGraph


class CapabilityAnalyzerContract(ABC):
    """Contract for analyzing capability requirements from an ExecutionRequest."""

    @abstractmethod
    def analyze_capabilities(self, execution_request: ExecutionRequest) -> CapabilityReport:
        """Extract and structure capability requirements from an execution request."""
        raise NotImplementedError


class OrganizationBuilderContract(ABC):
    """Contract for building engineering organization topology from capability reports."""

    @abstractmethod
    def build_organization(
        self, execution_request: ExecutionRequest, capability_report: CapabilityReport
    ) -> Organization:
        """Synthesize engineering organization structure, roles, and hierarchy."""
        raise NotImplementedError


class OrganizationValidatorContract(ABC):
    """Contract for validating organization integrity and boundary constraints."""

    @abstractmethod
    def validate_organization(self, organization: Organization) -> OrganizationReport:
        """Perform structural validation on an organization topology."""
        raise NotImplementedError


class SwarmGraphBuilderContract(ABC):
    """Contract for constructing multi-view Swarm Graphs from an Organization."""

    @abstractmethod
    def build_swarm_graph(self, organization: Organization) -> SwarmGraph:
        """Construct directed dependency, reporting, execution, review, and approval graphs."""
        raise NotImplementedError


class ExecutionBlueprintBuilderContract(ABC):
    """Contract for producing immutable Execution Blueprints."""

    @abstractmethod
    def create_blueprint(
        self,
        execution_request: ExecutionRequest,
        organization: Organization,
        capability_report: CapabilityReport,
        swarm_graph: SwarmGraph,
    ) -> ExecutionBlueprint:
        """Consolidate pipeline outputs into an immutable Execution Blueprint."""
        raise NotImplementedError
