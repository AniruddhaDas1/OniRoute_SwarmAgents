"""Project Assembly Certification Exceptions (Phase P4.G5)."""

from __future__ import annotations


class ProjectAssemblyError(Exception):
    """Base exception for Project Assembly certification failures."""

    pass


class AssemblyCertificationError(ProjectAssemblyError):
    """Raised when Project Assembly certification or freeze validation fails."""

    pass
