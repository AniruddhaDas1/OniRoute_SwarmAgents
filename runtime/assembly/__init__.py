"""Project Assembly Subsystem Package (Phase P4.G5).

Certifies and freezes the complete Project Assembly pipeline (P4.G1 through P4.G4).
"""

from runtime.assembly.certification import ProjectAssemblyCertificationEngine
from runtime.assembly.exceptions import AssemblyCertificationError, ProjectAssemblyError
from runtime.assembly.models import ProjectAssemblyCertificationReport

__all__ = [
    "ProjectAssemblyCertificationEngine",
    "ProjectAssemblyCertificationReport",
    "ProjectAssemblyError",
    "AssemblyCertificationError",
]
