"""Data models for Intent Analysis Engine (Phase P1.I1)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class IntentReport(BaseModel):
    """Immutable Intent Analysis report representing extracted engineering intent.

    Produced by IntentAnalyzer without modifying Mission, Organization,
    Blueprint, Collaboration, or Runtime execution layers.
    """

    model_config = ConfigDict(frozen=True)

    intent_id: str = Field(description="Unique intent report identifier (e.g. int-123456)")
    original_request: str = Field(description="Original raw prompt string from user")
    normalized_request: str = Field(description="Normalized request string")
    primary_intent: str = Field(description="Extracted primary engineering intent (build, refactor, fix, etc.)")
    project_category: str = Field(description="Identified project category (Website, CRM, Mobile App, etc.)")
    application_type: str = Field(description="Detected application runtime type (Web Application, Mobile Application, etc.)")
    detected_technologies: List[str] = Field(default_factory=list, description="Consolidated list of all detected technologies")
    detected_frameworks: List[str] = Field(default_factory=list, description="Detected application frameworks")
    detected_languages: List[str] = Field(default_factory=list, description="Detected programming languages")
    detected_database: List[str] = Field(default_factory=list, description="Detected database systems")
    detected_cloud: List[str] = Field(default_factory=list, description="Detected cloud platforms or infrastructure tools")
    detected_authentication: List[str] = Field(default_factory=list, description="Detected authentication solutions")
    detected_integrations: List[str] = Field(default_factory=list, description="Detected third-party APIs or integrations")
    detected_features: List[str] = Field(default_factory=list, description="Detected optional application features")
    detected_constraints: List[str] = Field(default_factory=list, description="Detected architectural or operational constraints")
    unknown_items: List[str] = Field(default_factory=list, description="Unrecognized terms or missing dimensions")
    confidence_score: float = Field(description="Overall intent confidence score (0.00 to 1.00)")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Categorized evidence matching source tokens")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
