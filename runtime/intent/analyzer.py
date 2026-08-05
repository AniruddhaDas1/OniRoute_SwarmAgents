"""IntentAnalyzer component for OniRoute Intent Analysis Engine (Phase P1.I1)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from runtime.mission.intake import MissionNormalizer
from runtime.workspace import WorkspaceManager

from .exceptions import EmptyRequestError
from .models import IntentReport
from .taxonomy import (
    APPLICATION_TYPE_MAP,
    AUTHENTICATION_TAXONOMY,
    CLOUD_TAXONOMY,
    CONSTRAINT_PATTERNS,
    DATABASE_TAXONOMY,
    FEATURE_PATTERNS,
    FRAMEWORKS_TAXONOMY,
    IMPLIED_STACK_RULES,
    INTEGRATIONS_TAXONOMY,
    LANGUAGES_TAXONOMY,
    PRIMARY_INTENT_PATTERNS,
    PROJECT_TYPE_PATTERNS,
    SUPPORTED_PROJECT_TYPES,
    UI_FRAMEWORKS_TAXONOMY,
)


class IntentAnalyzer:
    """Natural language engineering intent parser and analyzer.

    Transforms raw text into an immutable IntentReport without executing code,
    modifying mission files, or altering runtime architecture.
    """

    def __init__(self, workspace_manager: WorkspaceManager | None = None) -> None:
        self.workspace_manager = workspace_manager or WorkspaceManager()

    def analyze(
        self,
        raw_request: str,
        explicit_workspace: Path | None = None,
    ) -> IntentReport:
        """Analyze natural language request string and produce an immutable IntentReport."""
        if not raw_request or not raw_request.strip():
            raise EmptyRequestError("Natural language request cannot be empty or whitespace-only.")

        # 1. Normalize prompt using Mission Intake normalizer
        normalized = MissionNormalizer.normalize(raw_request)
        if not normalized:
            raise EmptyRequestError("Request string is empty after normalization.")

        now_utc = datetime.now(timezone.utc).isoformat()
        hash_id = abs(hash(f"{normalized}:{now_utc}")) % 1000000
        intent_id = f"int-{hash_id:06d}"

        evidence: Dict[str, Any] = {}

        # 2. Detect Primary Intent
        primary_intent = self._detect_primary_intent(normalized, evidence)

        # 3. Detect Project Category and Application Type
        project_category, application_type = self._detect_project_category(normalized, evidence)

        # 4. Detect Stack Components
        frameworks = self._match_taxonomy(normalized, FRAMEWORKS_TAXONOMY, "frameworks", evidence)
        languages = self._match_taxonomy(normalized, LANGUAGES_TAXONOMY, "languages", evidence)
        databases = self._match_taxonomy(normalized, DATABASE_TAXONOMY, "database", evidence)
        cloud = self._match_taxonomy(normalized, CLOUD_TAXONOMY, "cloud", evidence)
        auth = self._match_taxonomy(normalized, AUTHENTICATION_TAXONOMY, "authentication", evidence)
        integrations = self._match_taxonomy(normalized, INTEGRATIONS_TAXONOMY, "integrations", evidence)
        ui_frameworks = self._match_taxonomy(normalized, UI_FRAMEWORKS_TAXONOMY, "ui_frameworks", evidence)

        # 5. Apply Implied Stack Rules
        self._apply_implied_rules(
            frameworks=frameworks,
            languages=languages,
            databases=databases,
            cloud=cloud,
            auth=auth,
            evidence=evidence,
        )

        # Refine project_category if it was Unknown but implied by frameworks
        if project_category == "Unknown":
            for fw in list(frameworks):
                if fw in IMPLIED_STACK_RULES and "project_category" in IMPLIED_STACK_RULES[fw]:
                    project_category = IMPLIED_STACK_RULES[fw]["project_category"]
                    application_type = APPLICATION_TYPE_MAP.get(project_category, "Web Application")
                    evidence["project_category_implied"] = fw
                    break

        # 6. Consolidate detected technologies
        all_techs: Set[str] = set()
        all_techs.update(frameworks)
        all_techs.update(languages)
        all_techs.update(databases)
        all_techs.update(cloud)
        all_techs.update(auth)
        all_techs.update(integrations)
        all_techs.update(ui_frameworks)
        detected_technologies = sorted(list(all_techs))

        # 7. Extract Features & Constraints
        detected_features = self._match_patterns(normalized, FEATURE_PATTERNS, "features", evidence)
        detected_constraints = self._match_patterns(normalized, CONSTRAINT_PATTERNS, "constraints", evidence)

        # 8. Identify Unknown Items & Compute Confidence Score
        unknown_items, confidence_score = self._evaluate_confidence_and_unknowns(
            normalized=normalized,
            primary_intent=primary_intent,
            project_category=project_category,
            detected_technologies=detected_technologies,
            features=detected_features,
            evidence=evidence,
        )

        # 9. Build and return immutable IntentReport
        return IntentReport(
            intent_id=intent_id,
            original_request=raw_request,
            normalized_request=normalized,
            primary_intent=primary_intent,
            project_category=project_category,
            application_type=application_type,
            detected_technologies=detected_technologies,
            detected_frameworks=sorted(list(frameworks)),
            detected_languages=sorted(list(languages)),
            detected_database=sorted(list(databases)),
            detected_cloud=sorted(list(cloud)),
            detected_authentication=sorted(list(auth)),
            detected_integrations=sorted(list(integrations)),
            detected_features=sorted(list(detected_features)),
            detected_constraints=sorted(list(detected_constraints)),
            unknown_items=unknown_items,
            confidence_score=confidence_score,
            evidence=evidence,
            timestamp=now_utc,
        )

    def _detect_primary_intent(self, text: str, evidence: Dict[str, Any]) -> str:
        for pattern, intent_name in PRIMARY_INTENT_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                evidence["primary_intent"] = {"token": match.group(0), "intent": intent_name}
                return intent_name
        evidence["primary_intent"] = {"token": "default", "intent": "build"}
        return "build"

    def _detect_project_category(self, text: str, evidence: Dict[str, Any]) -> Tuple[str, str]:
        for pattern, category in PROJECT_TYPE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                app_type = APPLICATION_TYPE_MAP.get(category, "Web Application")
                evidence["project_category"] = {"token": match.group(0), "category": category}
                return category, app_type
        evidence["project_category"] = {"token": None, "category": "Unknown"}
        return "Unknown", "Unknown Application"

    def _match_taxonomy(
        self, text: str, taxonomy: Dict[str, str], key: str, evidence: Dict[str, Any]
    ) -> Set[str]:
        results: Set[str] = set()
        matches_evidence = []
        for pattern, tech_name in taxonomy.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                results.add(tech_name)
                matches_evidence.append({"token": match.group(0), "name": tech_name})
        if matches_evidence:
            evidence[key] = matches_evidence
        return results

    def _match_patterns(
        self, text: str, pattern_map: Dict[str, str], key: str, evidence: Dict[str, Any]
    ) -> Set[str]:
        results: Set[str] = set()
        matches_evidence = []
        for pattern, item_name in pattern_map.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                results.add(item_name)
                matches_evidence.append({"token": match.group(0), "item": item_name})
        if matches_evidence:
            evidence[key] = matches_evidence
        return results

    def _apply_implied_rules(
        self,
        frameworks: Set[str],
        languages: Set[str],
        databases: Set[str],
        cloud: Set[str],
        auth: Set[str],
        evidence: Dict[str, Any],
    ) -> None:
        implied_record = []
        for item in list(frameworks | databases | cloud):
            if item in IMPLIED_STACK_RULES:
                rule = IMPLIED_STACK_RULES[item]
                if "frameworks" in rule:
                    for f in rule["frameworks"]:
                        frameworks.add(f)
                        implied_record.append({"from": item, "implied_framework": f})
                if "languages" in rule:
                    for l in rule["languages"]:
                        languages.add(l)
                        implied_record.append({"from": item, "implied_language": l})
                if "database" in rule:
                    for d in rule["database"]:
                        databases.add(d)
                        implied_record.append({"from": item, "implied_database": d})
                if "cloud" in rule:
                    for c in rule["cloud"]:
                        cloud.add(c)
                        implied_record.append({"from": item, "implied_cloud": c})
        if implied_record:
            evidence["implied_stack"] = implied_record

    def _evaluate_confidence_and_unknowns(
        self,
        normalized: str,
        primary_intent: str,
        project_category: str,
        detected_technologies: List[str],
        features: Set[str],
        evidence: Dict[str, Any],
    ) -> Tuple[List[str], float]:
        unknowns: List[str] = []
        score = 0.0

        # 1. Primary Intent score (max 0.25)
        if evidence.get("primary_intent", {}).get("token") != "default":
            score += 0.25
        else:
            score += 0.20  # Implicit intent (defaulted to build)

        # 2. Project Category score (max 0.35)
        if project_category != "Unknown":
            score += 0.35
        else:
            unknowns.append("Project category could not be clearly identified")
            score += 0.05

        # 3. Technology Stack score (max 0.25)
        if len(detected_technologies) >= 2:
            score += 0.25
        elif len(detected_technologies) == 1:
            score += 0.15
        elif features:
            score += 0.10
        elif project_category != "Unknown":
            score += 0.15
        else:
            unknowns.append("No explicit technology stack detected")
            score += 0.05

        # 4. Specificity & Clarity score (max 0.15)
        words = normalized.split()
        if len(words) >= 3 and (project_category != "Unknown" or len(detected_technologies) > 0):
            score += 0.15
        elif len(words) >= 2 and project_category != "Unknown":
            score += 0.15
        elif project_category == "Unknown" and len(detected_technologies) == 0:
            unknowns.append(f"Unrecognized or ambiguous request terms: '{normalized}'")
            score = min(score, 0.30)

        final_score = round(min(max(score, 0.0), 1.0), 2)
        return unknowns, final_score
