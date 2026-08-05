"""Engineering Contracts Subsystem Package (Phase P4.G4).

Consumes ImplementationAllocationReport and produces EngineeringContractReport.
"""

from runtime.contracts.engine import DISCIPLINE_WAVE_MAP, EngineeringContractEngine
from runtime.contracts.exceptions import (
    ContractConstraintError,
    ContractValidationError,
    EngineeringContractError,
)
from runtime.contracts.models import EngineeringContract, EngineeringContractReport

__all__ = [
    "EngineeringContractEngine",
    "EngineeringContractReport",
    "EngineeringContract",
    "DISCIPLINE_WAVE_MAP",
    "EngineeringContractError",
    "ContractValidationError",
    "ContractConstraintError",
]
