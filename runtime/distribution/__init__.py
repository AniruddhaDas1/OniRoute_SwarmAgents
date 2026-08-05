"""Platform Distribution Subsystem Package (Phase P6.D4).

Installation, configuration, platform detection, and distribution preparation.
"""

from runtime.distribution.engine import (
    ONIROUTE_CODENAME,
    ONIROUTE_VERSION,
    ConfigurationManager,
    ConfigValidationResult,
    DistributionPreparer,
    InitializationEngine,
    InitializationResult,
    OniRouteConfig,
    PlatformDetector,
    PlatformInfo,
)

__all__ = [
    "ONIROUTE_VERSION",
    "ONIROUTE_CODENAME",
    "PlatformDetector",
    "PlatformInfo",
    "InitializationEngine",
    "InitializationResult",
    "ConfigurationManager",
    "ConfigValidationResult",
    "OniRouteConfig",
    "DistributionPreparer",
]
