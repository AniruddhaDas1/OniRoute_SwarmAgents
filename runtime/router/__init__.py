"""Natural Language Router Subsystem Package (Phase P6.D1).

Public entry point for natural language requests ("oniroute build real estate website",
"oniroute create SaaS CRM").
"""

from runtime.router.exceptions import ConfidenceBelowThresholdError, RouterError, RouterExecutionError
from runtime.router.models import RouterExecutionResult, SmartDefaults
from runtime.router.router import NaturalLanguageRouter

__all__ = [
    "NaturalLanguageRouter",
    "SmartDefaults",
    "RouterExecutionResult",
    "RouterError",
    "RouterExecutionError",
    "ConfidenceBelowThresholdError",
]
