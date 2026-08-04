class GovernanceError(Exception):pass
class PolicyDeniedError(GovernanceError):pass
class BudgetExceededError(GovernanceError):pass
