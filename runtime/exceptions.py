class OniRouteError(Exception):
    """Base runtime error."""


class LoadError(OniRouteError):
    """Raised when repository metadata cannot be loaded."""


class DuplicateIdentifierError(OniRouteError):
    """Raised when strict registration encounters a duplicate identifier."""
