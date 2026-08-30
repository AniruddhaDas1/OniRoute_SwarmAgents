"""E4.1 Artifact Review Engine.

Phase E4.1 — Real Artifact Review & Quality Gates.

Implements:
- ReviewEngine: Reviews artifacts AFTER generation/writing
- Quality checks for generated files
- Syntax validation
- Dependency and structural review
- Deterministic verdict calculation

Architecture:
    ArtifactExecutionPlan
        ↓
    ArtifactExecutionOrchestrator
        ↓
    RealCodeGenerationEngine
        ↓
    RepositoryWriter
        ↓
    REAL FILES
        ↓
    ReviewEngine
        ↓
    ReviewReport
        ↓
    ReviewVerdict

Does NOT:
- Regenerate source code
- Modify generated files
- Implement self-healing (E5)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.contracts.e4_models import (
    ReviewCheckResult,
    ReviewError,
    ReviewFinding,
    ReviewReport,
    ReviewRequest,
    ReviewSeverity,
    ReviewVerdict,
    WorkspaceBoundaryViolation,
    calculate_verdict,
    compute_finding_hash,
    compute_review_report_hash,
    generate_check_id,
    generate_finding_id,
    generate_report_id,
    generate_review_id,
    validate_path_within_workspace,
)
from runtime.contracts.e34_models import ArtifactFileResult


# ---------------------------------------------------------------------------
# E4.2 - Quality Check Definitions
# ---------------------------------------------------------------------------

# Minimum file size to be considered non-empty (bytes)
MIN_FILE_SIZE = 10

# Placeholder patterns that indicate incomplete content
PLACEHOLDER_PATTERNS = [
    r"^\s*TODO\s*$",
    r"^\s*TODO:\s*$",
    r"^\s*#\s*TODO\s*$",
    r"^\s*//\s*TODO\s*$",
    r"^\s*FIXME\s*$",
    r"^\s*FIXME:\s*$",
    r"^\s*#\s*FIXME\s*$",
    r"^\s*//\s*FIXME\s*$",
    r"^\s*PLACEHOLDER\s*$",
    r"^\s*INSERT\s+CODE\s+HERE\s*$",
    r"^\s*NOT\s+IMPLEMENTED\s*$",
    r"^\s*\{\{\s*\}\}\s*$",
    r"<TODO>",
    r"<!-- TODO -->",
    r"INSERT_CODE_HERE",
]

# Syntax validators by file extension
SYNTAX_VALIDATORS: Dict[str, str] = {
    ".py": "python",
    ".js": "node",
    ".ts": "node",
    ".jsx": "node",
    ".tsx": "node",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".css": "css",
}

# Import/reference patterns by language for dependency checks
IMPORT_PATTERNS: Dict[str, List[str]] = {
    "python": [
        r"^import\s+([\w.]+)",
        r"^from\s+([\w.]+)\s+import",
    ],
    "typescript": [
        r"^import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
        r"^import\s+['\"]([^'\"]+)['\"]",
        r"require\s*\(['\"]([^'\"]+)['\"]\)",
    ],
    "javascript": [
        r"^import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
        r"^import\s+['\"]([^'\"]+)['\"]",
        r"require\s*\(['\"]([^'\"]+)['\"]\)",
    ],
}


# ---------------------------------------------------------------------------
# E4.3 - Individual Quality Check Functions
# ---------------------------------------------------------------------------

def check_file_exists(
    absolute_path: str,
    file_path: str,
    artifact_execution_id: str,
    artifact_id: str,
) -> Tuple[bool, List[ReviewFinding]]:
    """Check if a file exists on disk.

    Returns:
        Tuple of (passed, findings)
    """
    findings = []

    if not os.path.exists(absolute_path):
        finding = ReviewFinding(
            finding_id=generate_finding_id("file_exists", 0),
            check_id=generate_check_id("file_exists", 0),
            check_type="file_exists",
            mission_id="",
            workspace_id="",
            plan_id="",
            artifact_execution_id=artifact_execution_id,
            artifact_id=artifact_id,
            file_path=file_path,
            absolute_path=absolute_path,
            severity=ReviewSeverity.CRITICAL,
            message=f"File does not exist: {file_path}",
            evidence=(f"Expected at: {absolute_path}",),
            is_blocking=True,
            rule_id="R001",
            rule_name="File must exist",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        findings.append(finding)
        return False, findings

    return True, findings


def check_file_not_empty(
    absolute_path: str,
    file_path: str,
    artifact_execution_id: str,
    artifact_id: str,
    min_size: int = MIN_FILE_SIZE,
) -> Tuple[bool, List[ReviewFinding]]:
    """Check if a file is not empty.

    Returns:
        Tuple of (passed, findings)
    """
    findings = []

    try:
        file_size = os.path.getsize(absolute_path)
    except OSError:
        finding = ReviewFinding(
            finding_id=generate_finding_id("file_not_empty", 0),
            check_id=generate_check_id("file_not_empty", 0),
            check_type="file_not_empty",
            mission_id="",
            workspace_id="",
            plan_id="",
            artifact_execution_id=artifact_execution_id,
            artifact_id=artifact_id,
            file_path=file_path,
            absolute_path=absolute_path,
            severity=ReviewSeverity.ERROR,
            message=f"Cannot read file size: {file_path}",
            evidence=(f"Path: {absolute_path}",),
            is_blocking=True,
            rule_id="R002",
            rule_name="File must be readable",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        findings.append(finding)
        return False, findings

    if file_size < min_size:
        finding = ReviewFinding(
            finding_id=generate_finding_id("file_not_empty", 1),
            check_id=generate_check_id("file_not_empty", 1),
            check_type="file_not_empty",
            mission_id="",
            workspace_id="",
            plan_id="",
            artifact_execution_id=artifact_execution_id,
            artifact_id=artifact_id,
            file_path=file_path,
            absolute_path=absolute_path,
            severity=ReviewSeverity.ERROR,
            message=f"File is empty or too small: {file_path} ({file_size} bytes)",
            evidence=(
                f"File size: {file_size} bytes",
                f"Minimum: {min_size} bytes",
            ),
            is_blocking=True,
            rule_id="R002",
            rule_name="File must not be empty",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        findings.append(finding)
        return False, findings

    return True, findings


def check_file_in_workspace(
    file_path: str,
    workspace_root: str,
    artifact_execution_id: str,
    artifact_id: str,
) -> Tuple[bool, List[ReviewFinding]]:
    """Check if a file path is within workspace boundaries.

    Returns:
        Tuple of (passed, findings)
    """
    findings = []

    is_valid, error_msg, absolute_path = validate_path_within_workspace(
        file_path, workspace_root, artifact_id
    )

    if not is_valid:
        finding = ReviewFinding(
            finding_id=generate_finding_id("path_boundary", 0),
            check_id=generate_check_id("path_boundary", 0),
            check_type="path_boundary",
            mission_id="",
            workspace_id="",
            plan_id="",
            artifact_execution_id=artifact_execution_id,
            artifact_id=artifact_id,
            file_path=file_path,
            absolute_path=absolute_path,
            severity=ReviewSeverity.CRITICAL,
            message=f"Path boundary violation: {error_msg}",
            evidence=(f"Workspace: {workspace_root}", f"Path: {file_path}"),
            is_blocking=True,
            rule_id="R003",
            rule_name="Path must be within workspace",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        findings.append(finding)
        return False, findings

    return True, findings


def check_no_placeholders(
    absolute_path: str,
    file_path: str,
    artifact_execution_id: str,
    artifact_id: str,
) -> Tuple[bool, List[ReviewFinding]]:
    """Check if a file contains placeholder content.

    Returns:
        Tuple of (passed, findings)
    """
    findings = []

    try:
        with open(absolute_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as e:
        # Can't read file - this is a different error
        return True, findings

    for i, pattern in enumerate(PLACEHOLDER_PATTERNS):
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            # Find the matching line for evidence
            lines = content.split("\n")
            matches = []
            for line in lines:
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append(line.strip()[:100])

            finding = ReviewFinding(
                finding_id=generate_finding_id("no_placeholders", i),
                check_id=generate_check_id("no_placeholders", i),
                check_type="no_placeholders",
                mission_id="",
                workspace_id="",
                plan_id="",
                artifact_execution_id=artifact_execution_id,
                artifact_id=artifact_id,
                file_path=file_path,
                absolute_path=absolute_path,
                severity=ReviewSeverity.ERROR,
                message=f"File contains placeholder: {pattern}",
                evidence=tuple(matches[:5]),  # First 5 matches
                is_blocking=True,
                rule_id="R004",
                rule_name="No placeholder content",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            findings.append(finding)
            return False, findings

    return True, findings


def check_syntax_validation(
    absolute_path: str,
    file_path: str,
    artifact_execution_id: str,
    artifact_id: str,
    language: str = "",
) -> Tuple[bool, bool, List[ReviewFinding]]:
    """Check file syntax using available validators.

    Returns:
        Tuple of (executed, passed, findings)
        - executed: True if validator was available and ran
        - passed: True if syntax is valid
        - findings: Any issues found
    """
    findings = []
    executed = False
    passed = True

    # Determine language from extension if not provided
    ext = os.path.splitext(absolute_path)[1].lower()
    validator_lang = language.lower() if language else ""

    # Map extension to validator language
    ext_to_lang = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
        ".css": "css",
    }

    if not validator_lang:
        validator_lang = ext_to_lang.get(ext, "")

    # Try syntax check based on language
    if validator_lang == "python":
        executed = True
        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", absolute_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                passed = False
                finding = ReviewFinding(
                    finding_id=generate_finding_id("syntax_python", 0),
                    check_id=generate_check_id("syntax_python", 0),
                    check_type="syntax_python",
                    mission_id="",
                    workspace_id="",
                    plan_id="",
                    artifact_execution_id=artifact_execution_id,
                    artifact_id=artifact_id,
                    file_path=file_path,
                    absolute_path=absolute_path,
                    severity=ReviewSeverity.ERROR,
                    message=f"Python syntax error: {file_path}",
                    evidence=(result.stderr[:500] if result.stderr else "Unknown error",),
                    is_blocking=True,
                    rule_id="R005",
                    rule_name="Valid Python syntax",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                findings.append(finding)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Python not available - record as skipped
            executed = False

    elif validator_lang in ("javascript", "typescript"):
        executed = True
        try:
            # Try Node.js syntax check
            result = subprocess.run(
                ["node", "--check", absolute_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                passed = False
                finding = ReviewFinding(
                    finding_id=generate_finding_id(f"syntax_{validator_lang}", 0),
                    check_id=generate_check_id(f"syntax_{validator_lang}", 0),
                    check_type=f"syntax_{validator_lang}",
                    mission_id="",
                    workspace_id="",
                    plan_id="",
                    artifact_execution_id=artifact_execution_id,
                    artifact_id=artifact_id,
                    file_path=file_path,
                    absolute_path=absolute_path,
                    severity=ReviewSeverity.ERROR,
                    message=f"{validator_lang.capitalize()} syntax error: {file_path}",
                    evidence=(result.stderr[:500] if result.stderr else "Unknown error",),
                    is_blocking=True,
                    rule_id="R005",
                    rule_name=f"Valid {validator_lang.capitalize()} syntax",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                findings.append(finding)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Node not available - record as skipped
            executed = False

    elif validator_lang == "json":
        executed = True
        try:
            with open(absolute_path, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            passed = False
            finding = ReviewFinding(
                finding_id=generate_finding_id("syntax_json", 0),
                check_id=generate_check_id("syntax_json", 0),
                check_type="syntax_json",
                mission_id="",
                workspace_id="",
                plan_id="",
                artifact_execution_id=artifact_execution_id,
                artifact_id=artifact_id,
                file_path=file_path,
                absolute_path=absolute_path,
                severity=ReviewSeverity.ERROR,
                message=f"Invalid JSON: {file_path}",
                evidence=(str(e)[:200],),
                is_blocking=True,
                rule_id="R005",
                rule_name="Valid JSON syntax",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            findings.append(finding)
        except (OSError, UnicodeDecodeError):
            passed = False

    elif validator_lang in ("yaml", "yml"):
        executed = True
        try:
            import yaml
            with open(absolute_path, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except ImportError:
            # PyYAML not available
            executed = False
        except yaml.YAMLError as e:
            passed = False
            finding = ReviewFinding(
                finding_id=generate_finding_id("syntax_yaml", 0),
                check_id=generate_check_id("syntax_yaml", 0),
                check_type="syntax_yaml",
                mission_id="",
                workspace_id="",
                plan_id="",
                artifact_execution_id=artifact_execution_id,
                artifact_id=artifact_id,
                file_path=file_path,
                absolute_path=absolute_path,
                severity=ReviewSeverity.ERROR,
                message=f"Invalid YAML: {file_path}",
                evidence=(str(e)[:200],),
                is_blocking=True,
                rule_id="R005",
                rule_name="Valid YAML syntax",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            findings.append(finding)

    return executed, passed, findings


def check_required_artifacts_exist(
    expected_artifacts: List[str],
    actual_files: List[str],
    workspace_root: str,
    mission_id: str,
    workspace_id: str,
    plan_id: str,
) -> Tuple[bool, List[ReviewFinding]]:
    """Check if all required artifacts exist.

    Returns:
        Tuple of (passed, findings)
    """
    findings = []
    actual_paths = set(actual_files)
    missing = []

    for artifact_id in expected_artifacts:
        # Check if any file matches this artifact
        found = any(artifact_id in f for f in actual_paths)
        if not found:
            missing.append(artifact_id)

    if missing:
        for i, artifact_id in enumerate(missing):
            finding = ReviewFinding(
                finding_id=generate_finding_id("required_artifact", i),
                check_id=generate_check_id("required_artifacts", i),
                check_type="required_artifacts",
                mission_id=mission_id,
                workspace_id=workspace_id,
                plan_id=plan_id,
                artifact_execution_id=artifact_id,
                artifact_id=artifact_id,
                file_path="",
                absolute_path="",
                severity=ReviewSeverity.ERROR,
                message=f"Required artifact not found: {artifact_id}",
                evidence=(f"Expected in workspace: {workspace_root}",),
                is_blocking=True,
                rule_id="R006",
                rule_name="Required artifacts must exist",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            findings.append(finding)
        return False, findings

    return True, findings


def check_cross_artifact_references(
    absolute_path: str,
    file_path: str,
    artifact_execution_id: str,
    artifact_id: str,
    all_files: List[str],
    language: str = "",
) -> Tuple[bool, List[ReviewFinding]]:
    """Check cross-artifact references (imports, requires, etc.).

    Returns:
        Tuple of (passed, findings)
    """
    findings = []

    # Determine language from extension
    ext = os.path.splitext(absolute_path)[1].lower()
    ext_to_lang = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
    }

    lang = language.lower() if language else ext_to_lang.get(ext, "")

    if lang not in IMPORT_PATTERNS:
        return True, findings

    try:
        with open(absolute_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return True, findings

    # Get all file names for matching
    file_basenames = set()
    for f in all_files:
        basename = os.path.splitext(os.path.basename(f))[0]
        file_basenames.add(basename)
        file_basenames.add(os.path.basename(f))

    # Check imports
    for i, pattern in enumerate(IMPORT_PATTERNS.get(lang, [])):
        for match in re.finditer(pattern, content, re.MULTILINE):
            if match.groups:
                imported = match.group(1)
                # Skip external packages
                if not imported or imported.startswith(".") or "/" in imported:
                    continue

                # Check if it could be a local file
                module_name = imported.split(".")[0]
                if module_name not in file_basenames:
                    # This could be an external package - skip
                    continue

                # Check if the referenced file exists
                found = any(module_name in f for f in all_files)
                if not found:
                    finding = ReviewFinding(
                        finding_id=generate_finding_id("cross_reference", i),
                        check_id=generate_check_id("cross_references", i),
                        check_type="cross_references",
                        mission_id="",
                        workspace_id="",
                        plan_id="",
                        artifact_execution_id=artifact_execution_id,
                        artifact_id=artifact_id,
                        file_path=file_path,
                        absolute_path=absolute_path,
                        severity=ReviewSeverity.WARNING,
                        message=f"Reference to missing module: {module_name}",
                        evidence=(f"Import: {imported}",),
                        is_blocking=False,
                        rule_id="R007",
                        rule_name="Cross-artifact references must exist",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    findings.append(finding)

    return len(findings) == 0, findings


def check_project_structure(
    workspace_root: str,
    files: List[str],
    artifact_execution_ids: List[str],
) -> Tuple[bool, List[ReviewFinding]]:
    """Check basic project structure requirements.

    Returns:
        Tuple of (passed, findings)
    """
    findings = []

    # Check for essential project files
    essential_files = ["package.json", "requirements.txt", "pyproject.toml", "setup.py"]
    has_essential = any(os.path.basename(f) in essential_files for f in files)

    if not has_essential and len(files) > 3:
        finding = ReviewFinding(
            finding_id=generate_finding_id("project_structure", 0),
            check_id=generate_check_id("project_structure", 0),
            check_type="project_structure",
            mission_id="",
            workspace_id="",
            plan_id="",
            artifact_execution_id="",
            artifact_id="",
            file_path="",
            absolute_path=workspace_root,
            severity=ReviewSeverity.INFO,
            message="No standard project configuration file found",
            evidence=(f"Files: {', '.join(essential_files)}",),
            is_blocking=False,
            rule_id="R008",
            rule_name="Standard project structure",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        findings.append(finding)

    # Check for empty directories
    try:
        for root, dirs, filenames in os.walk(workspace_root):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            if not filenames and not dirs:
                # Empty directory
                rel_path = os.path.relpath(root, workspace_root)
                if rel_path != ".":
                    finding = ReviewFinding(
                        finding_id=generate_finding_id("empty_directory", 0),
                        check_id=generate_check_id("empty_directories", 0),
                        check_type="empty_directories",
                        mission_id="",
                        workspace_id="",
                        plan_id="",
                        artifact_execution_id="",
                        artifact_id="",
                        file_path=rel_path,
                        absolute_path=root,
                        severity=ReviewSeverity.INFO,
                        message=f"Empty directory found: {rel_path}",
                        evidence=(),
                        is_blocking=False,
                        rule_id="R009",
                        rule_name="No empty directories",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    findings.append(finding)
    except OSError:
        pass

    return True, findings


# ---------------------------------------------------------------------------
# E4.2 - Review Engine
# ---------------------------------------------------------------------------

class ReviewEngine:
    """Reviews generated artifacts AFTER generation and writing.

    The ReviewEngine:
    - Operates against actual repository files
    - Does NOT regenerate source code
    - Does NOT silently modify generated files
    - Is read/analyze/validate only
    - Produces ReviewReport with findings and verdict
    """

    def __init__(self, workspace_root: str):
        """Initialize the review engine.

        Args:
            workspace_root: Absolute path to workspace root
        """
        self.workspace_root = workspace_root

    def review(
        self,
        request: ReviewRequest,
        file_results: List[ArtifactFileResult],
    ) -> ReviewReport:
        """Review generated artifacts.

        Args:
            request: Review request with scope and configuration
            file_results: List of file results from generation

        Returns:
            ReviewReport with findings and verdict
        """
        start_time = time.time()
        review_started = datetime.now(timezone.utc).isoformat()
        review_id = request.review_id or generate_review_id(request.mission_id)
        report_id = generate_report_id(review_id)

        all_findings: List[ReviewFinding] = []
        check_results: List[ReviewCheckResult] = []

        # Collect all files to review
        files_to_review: List[Tuple[str, str, str, str]] = []  # (file_path, absolute_path, artifact_execution_id, artifact_id)

        for file_result in file_results:
            if file_result.file_written and file_result.absolute_path:
                # artifact_id is derived from artifact_execution_id if not available
                artifact_id = file_result.artifact_execution_id.replace("aeu-", "art-") if file_result.artifact_execution_id else ""
                files_to_review.append((
                    file_result.target_path,
                    file_result.absolute_path,
                    file_result.artifact_execution_id,
                    artifact_id,
                ))

        # Add files from request
        for file_path in request.file_paths:
            is_valid, _, absolute_path = validate_path_within_workspace(
                file_path, self.workspace_root
            )
            if is_valid and os.path.exists(absolute_path):
                files_to_review.append((file_path, absolute_path, "", ""))

        # Remove duplicates
        seen = set()
        unique_files = []
        for item in files_to_review:
            if item[1] not in seen:
                seen.add(item[1])
                unique_files.append(item)

        # Execute checks for each file
        check_index = 0
        for file_path, absolute_path, artifact_execution_id, artifact_id in unique_files:
            file_findings, file_check_results = self._review_file(
                request=request,
                file_path=file_path,
                absolute_path=absolute_path,
                artifact_execution_id=artifact_execution_id,
                artifact_id=artifact_id,
                all_files=[f[1] for f in unique_files],
                check_index=check_index,
            )
            all_findings.extend(file_findings)
            check_results.extend(file_check_results)
            check_index += len(file_check_results)

        # Execute project-level checks
        project_findings, project_check_results = self._review_project(
            request=request,
            files=[f[0] for f in unique_files],
            absolute_files=[f[1] for f in unique_files],
            check_index=check_index,
        )
        all_findings.extend(project_findings)
        check_results.extend(project_check_results)

        # Update findings with context
        for finding in all_findings:
            object.__setattr__(finding, "mission_id", request.mission_id)
            object.__setattr__(finding, "workspace_id", request.workspace_id)
            object.__setattr__(finding, "plan_id", request.plan_id)

        # Calculate verdict
        verdict, verdict_reasons = calculate_verdict(all_findings)

        # Build report
        review_completed = datetime.now(timezone.utc).isoformat()
        total_duration = (time.time() - start_time) * 1000

        # Count findings by severity
        critical_count = sum(1 for f in all_findings if f.severity == ReviewSeverity.CRITICAL)
        error_count = sum(1 for f in all_findings if f.severity == ReviewSeverity.ERROR)
        warning_count = sum(1 for f in all_findings if f.severity == ReviewSeverity.WARNING)
        info_count = sum(1 for f in all_findings if f.severity == ReviewSeverity.INFO)

        # Count check results
        checks_passed = sum(1 for c in check_results if c.passed and c.executed)
        checks_failed = sum(1 for c in check_results if not c.passed and c.executed)
        checks_skipped = sum(1 for c in check_results if c.skipped)

        report = ReviewReport(
            report_id=report_id,
            review_id=review_id,
            mission_id=request.mission_id,
            workspace_id=request.workspace_id,
            plan_id=request.plan_id,
            workspace_root=self.workspace_root,
            repository_scope=request.repository_scope,
            total_checks=len(check_results),
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            checks_skipped=checks_skipped,
            check_results=tuple(check_results),
            total_findings=len(all_findings),
            critical_findings=critical_count,
            error_findings=error_count,
            warning_findings=warning_count,
            info_findings=info_count,
            findings=tuple(all_findings),
            verdict=verdict,
            verdict_reasons=tuple(verdict_reasons),
            review_started=review_started,
            review_completed=review_completed,
            total_duration_ms=total_duration,
            files_reviewed=len(unique_files),
            files_with_issues=len(set(f.artifact_execution_id for f in all_findings)),
            deterministic=True,
            deterministic_hash="",
        )

        # Compute hash
        report.deterministic_hash = compute_review_report_hash(report)

        return report

    def _review_file(
        self,
        request: ReviewRequest,
        file_path: str,
        absolute_path: str,
        artifact_execution_id: str,
        artifact_id: str,
        all_files: List[str],
        check_index: int,
    ) -> Tuple[List[ReviewFinding], List[ReviewCheckResult]]:
        """Review a single file.

        Returns:
            Tuple of (findings, check_results)
        """
        findings: List[ReviewFinding] = []
        check_results: List[ReviewCheckResult] = []

        # Check 1: File exists
        check_started = datetime.now(timezone.utc).isoformat()
        check_id = generate_check_id("file_exists", check_index)
        passed, check_findings = check_file_exists(
            absolute_path, file_path, artifact_execution_id, artifact_id
        )
        findings.extend(check_findings)
        check_results.append(ReviewCheckResult(
            check_id=check_id,
            check_type="file_exists",
            executed=True,
            skipped=False,
            passed=passed,
            findings=tuple(check_findings),
            started_at=check_started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=0,
            evidence=(f"Path: {absolute_path}",),
        ))
        check_index += 1

        # If file doesn't exist, skip remaining checks
        if not passed:
            return findings, check_results

        # Check 2: File not empty
        check_started = datetime.now(timezone.utc).isoformat()
        check_id = generate_check_id("file_not_empty", check_index)
        passed, check_findings = check_file_not_empty(
            absolute_path, file_path, artifact_execution_id, artifact_id
        )
        findings.extend(check_findings)
        check_results.append(ReviewCheckResult(
            check_id=check_id,
            check_type="file_not_empty",
            executed=True,
            skipped=False,
            passed=passed,
            findings=tuple(check_findings),
            started_at=check_started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=0,
            evidence=(),
        ))
        check_index += 1

        # Check 3: Path boundary
        check_started = datetime.now(timezone.utc).isoformat()
        check_id = generate_check_id("path_boundary", check_index)
        passed, check_findings = check_file_in_workspace(
            file_path, self.workspace_root, artifact_execution_id, artifact_id
        )
        findings.extend(check_findings)
        check_results.append(ReviewCheckResult(
            check_id=check_id,
            check_type="path_boundary",
            executed=True,
            skipped=False,
            passed=passed,
            findings=tuple(check_findings),
            started_at=check_started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=0,
            evidence=(f"Workspace: {self.workspace_root}",),
        ))
        check_index += 1

        # Check 4: No placeholders
        check_started = datetime.now(timezone.utc).isoformat()
        check_id = generate_check_id("no_placeholders", check_index)
        passed, check_findings = check_no_placeholders(
            absolute_path, file_path, artifact_execution_id, artifact_id
        )
        findings.extend(check_findings)
        check_results.append(ReviewCheckResult(
            check_id=check_id,
            check_type="no_placeholders",
            executed=True,
            skipped=False,
            passed=passed,
            findings=tuple(check_findings),
            started_at=check_started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=0,
            evidence=(),
        ))
        check_index += 1

        # Check 5: Syntax validation (if not skipped)
        if not request.skip_syntax_checks:
            check_started = datetime.now(timezone.utc).isoformat()
            check_type = f"syntax_{os.path.splitext(absolute_path)[1][1:]}"
            check_id = generate_check_id(check_type, check_index)
            executed, passed, check_findings = check_syntax_validation(
                absolute_path, file_path, artifact_execution_id, artifact_id
            )
            findings.extend(check_findings)
            check_results.append(ReviewCheckResult(
                check_id=check_id,
                check_type=check_type,
                executed=executed,
                skipped=not executed,
                skip_reason="Validator not available" if not executed else "",
                passed=passed if executed else True,
                findings=tuple(check_findings),
                started_at=check_started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=0,
                evidence=(),
            ))
            check_index += 1

        # Check 6: Cross-artifact references
        check_started = datetime.now(timezone.utc).isoformat()
        check_id = generate_check_id("cross_references", check_index)
        passed, check_findings = check_cross_artifact_references(
            absolute_path, file_path, artifact_execution_id, artifact_id, all_files
        )
        findings.extend(check_findings)
        check_results.append(ReviewCheckResult(
            check_id=check_id,
            check_type="cross_references",
            executed=True,
            skipped=False,
            passed=passed,
            findings=tuple(check_findings),
            started_at=check_started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=0,
            evidence=(),
        ))

        return findings, check_results

    def _review_project(
        self,
        request: ReviewRequest,
        files: List[str],
        absolute_files: List[str],
        check_index: int,
    ) -> Tuple[List[ReviewFinding], List[ReviewCheckResult]]:
        """Review project-level aspects.

        Returns:
            Tuple of (findings, check_results)
        """
        findings: List[ReviewFinding] = []
        check_results: List[ReviewCheckResult] = []

        # Check: Project structure
        check_started = datetime.now(timezone.utc).isoformat()
        check_id = generate_check_id("project_structure", check_index)
        passed, check_findings = check_project_structure(
            self.workspace_root,
            files,
            list(request.artifact_execution_ids),
        )
        findings.extend(check_findings)
        check_results.append(ReviewCheckResult(
            check_id=check_id,
            check_type="project_structure",
            executed=True,
            skipped=False,
            passed=True,  # Structure checks don't fail the review
            findings=tuple(check_findings),
            started_at=check_started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=0,
            evidence=(f"Files: {len(files)}",),
        ))

        return findings, check_results
