"""Engineering Contracts Exceptions (Phase P4.G4)."""

from __future__ import annotations


class EngineeringContractError(Exception):
    """Base exception for engineering contract failures."""

    pass


class ContractValidationError(EngineeringContractError):
    """Raised when engineering contract validation checks fail."""

    pass


class ContractDependencyError(EngineeringContractError):
 """Raised when a circular dependency or invalid dependency is detected among engineering contracts."""

 pass


class ContractCoverageError(EngineeringContractError):
 """Raised when contract coverage is below 100%."""

 pass


class ContractConstraintError(EngineeringContractError):
 """Raised when constraint completeness or dependency validation fails."""

 pass
