"""Workspace Scaffold Data Contracts (Phase P4.G1)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class WorkspaceScaffoldReport(BaseModel):
    """Immutable Workspace Scaffold Report contract produced by WorkspaceScaffoldEngine."""

    model_config = ConfigDict(frozen=True)

    scaffold_id: str = Field(..., description="Unique scaffold report identifier (scaf-xxxxxx)")
    workspace_id: str = Field(..., description="Target workspace identifier")
    workspace_root: str = Field(..., description="Absolute path string of the workspace root")
    technology_stack: str = Field(..., description="Target technology stack (e.g. react, nextjs, python, fastapi, flutter, monorepo)")
    created_directories: List[str] = Field(default_factory=list, description="Relative paths of initialized workspace directories")
    created_files: List[str] = Field(default_factory=list, description="Relative paths of scaffolded configuration and build files")
    configuration_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of configuration files and markers created")
    scaffold_hash: str = Field(..., description="SHA-256 hash of scaffold structure and metadata")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Scaffold validation metrics and execution evidence")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of scaffold completion")
