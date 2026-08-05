"""Engineering Contracts Exceptions (Phase P4.G4)."""

from __future__ import annotations


class EngineeringContractError(Exception):
    """Base exception for engineering contract failures."""

    pass


class ContractValidationError(EngineeringContractError):
    """Raised when engineering contract validation checks fail."""

    pass


class ContractConstraintError(EngineeringContractError):
    """Raised when constraint completeness or dependency validation fails."""

    pass
