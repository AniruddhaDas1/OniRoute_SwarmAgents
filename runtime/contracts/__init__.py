from __future__ import annotations

from runtime.contracts.builder import EngineeringContractBuilder
from runtime.contracts.decomposition import (
    ACCEPTANCE_CRITERIA_TEMPLATES,
    ArtifactRoute,
    CONTRACT_DECOMPOSITION_RULES,
    CONTRACT_DELIVERABLE_TYPE,
    CONTRACT_REPOSITORY_SCOPE,
    CONTRACT_VERIFICATION_METHOD,
    ContractDecompositionError,
    ContractDecompositionReport,
    ContractDecompositionValidator,
    DependencyEdge,
    DependencyGraph,
    DependencyType,
    DecompositionCoverageMetrics,
    DeterminismError,
    DuplicateIDError,
    ExecutionWave,
    ParallelExecutionGroup,
    SubContract,
    TechnologyMismatchError,
    TraceabilityError,
    ValidationError,
    WaveOrderingError,
)
from runtime.contracts.decomposer import ContractDecompositionEngine
from runtime.contracts.e21_models import (
    ACCEPTANCE_CRITERIA_TEMPLATES as E21_AC_TEMPLATES,
    DELIVERABLE_VERIFICATION_METHOD,
    DISCIPLINE_DELIVERABLE_TYPE,
    DISCIPLINE_REPOSITORY_SCOPE,
    PRIORITY_RANK,
    SKILL_PRIORITY_TO_GENERATION,
    AcceptanceCriteria,
    ContractCoverageMetrics,
    ContractTraceability,
    DeliverableContract,
)
from runtime.contracts.engine import DISCIPLINE_WAVE_MAP, EngineeringContractEngine
from runtime.contracts.exceptions import (
    ContractConstraintError,
    ContractCoverageError,
    ContractDependencyError,
    ContractValidationError,
    EngineeringContractError,
)
from runtime.contracts.models import EngineeringContract, EngineeringContractReport
from runtime.contracts.validation import ContractValidator

__all__ = [
    # P4.G4 core
    "EngineeringContractEngine",
    "EngineeringContractReport",
    "EngineeringContract",
    "DISCIPLINE_WAVE_MAP",
    "EngineeringContractError",
    "ContractValidationError",
    "ContractConstraintError",
    # E2.1 builder
    "EngineeringContractBuilder",
    # E2.1 validator
    "ContractValidator",
    # E2.1 extended models
    "ContractCoverageMetrics",
    "ContractCoverageError",
    "ContractDependencyError",
    "DeliverableContract",
    "AcceptanceCriteria",
    "ContractTraceability",
    # E2.2 decomposition
    "ContractDecompositionEngine",
    "ContractDecompositionReport",
    "SubContract",
    "DependencyGraph",
    "DependencyEdge",
    "DependencyType",
    "ArtifactRoute",
    "ExecutionWave",
    "ParallelExecutionGroup",
    "DecompositionCoverageMetrics",
    "ContractDecompositionValidator",
    "ContractDecompositionError",
    "ValidationError",
    "DeterminismError",
    "DuplicateIDError",
    "TechnologyMismatchError",
    "TraceabilityError",
    "WaveOrderingError",
    # Discipline mappings
    "DISCIPLINE_REPOSITORY_SCOPE",
    "DISCIPLINE_DELIVERABLE_TYPE",
    "DELIVERABLE_VERIFICATION_METHOD",
    "ACCEPTANCE_CRITERIA_TEMPLATES",
    "SKILL_PRIORITY_TO_GENERATION",
    "PRIORITY_RANK",
    # E2.2 mappings
    "CONTRACT_REPOSITORY_SCOPE",
    "CONTRACT_DELIVERABLE_TYPE",
    "CONTRACT_VERIFICATION_METHOD",
    "CONTRACT_DECOMPOSITION_RULES",
]
