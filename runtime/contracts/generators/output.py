"""E3.1 Output Normalizer and Content Validator.

Provides:
1. OutputNormalizer: Normalizes provider responses for extraction
2. ContentValidator: Validates generated content meets quality standards
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from runtime.contracts.e23_models import ArtifactExecutionUnit, GenerationStrategy
from runtime.contracts.e31_models import (
    ContentValidationCheck,
    ContentValidationResult,
    GeneratedContent,
    compute_content_hash,
    validate_content_not_empty,
    validate_content_no_placeholders,
    validate_language_match,
)


# Common code block patterns in LLM responses
CODE_BLOCK_PATTERNS = [
    r"```(\w+)?\n(.*?)\n```",  # ```language\ncode\n```
    r"```(\w+)?\n(.*?)```",  # ```language\ncode```
    r"```\n(.*?)\n```",  # ```\ncode\n```
    r"```(.*?)```",  # ```code```
]


class OutputNormalizer:
    """Normalizes LLM provider responses for artifact extraction.

    Provider responses often contain markdown code blocks, system reminders,
    and other wrapper content that needs to be stripped to get the actual
    artifact content.
    """

    def __init__(self):
        """Initialize the output normalizer."""
        self._code_block_re = re.compile(
            r"```(\w+)?\n(.*?)```",
            re.DOTALL | re.IGNORECASE
        )

    def normalize(
        self,
        content: str,
        expected_language: Optional[str] = None,
    ) -> str:
        """Normalize LLM output to extract artifact content.

        Args:
            content: Raw content from LLM provider
            expected_language: Expected programming language

        Returns:
            Normalized artifact content
        """
        if not content:
            return ""

        # Step 1: Extract code blocks
        extracted = self._extract_code_block(content, expected_language)
        if extracted:
            content = extracted

        # Step 2: Remove system reminders
        content = self._remove_system_reminders(content)

        # Step 3: Remove markdown headers and footers
        content = self._remove_markdown_wrappers(content)

        # Step 4: Remove trailing/leading whitespace but preserve structure
        content = self._strip_whitespace(content)

        return content

    def _extract_code_block(
        self,
        content: str,
        expected_language: Optional[str] = None,
    ) -> Optional[str]:
        """Extract content from code blocks.

        If multiple code blocks exist, prefer one matching expected language.
        """
        matches = list(self._code_block_re.finditer(content))

        if not matches:
            return None

        # If only one code block, use it
        if len(matches) == 1:
            match = matches[0]
            return match.group(2).strip()

        # Multiple code blocks - try to find one matching expected language
        if expected_language:
            for match in matches:
                lang = match.group(1)
                if lang and lang.lower() == expected_language.lower():
                    return match.group(2).strip()

        # No language match - use the largest code block
        largest = max(matches, key=lambda m: len(m.group(2)))
        return largest.group(2).strip()

    def _remove_system_reminders(self, content: str) -> str:
        """Remove system reminder blocks from content."""
        # Remove common system reminder patterns
        patterns = [
            r"<system-reminder>.*?</system-reminder>",
            r"<!-- system-reminder.*?-->",
            r"\[SYSTEM REMINDER\].*?\[/SYSTEM REMINDER\]",
        ]

        for pattern in patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE | re.DOTALL)

        return content

    def _remove_markdown_wrappers(self, content: str) -> str:
        """Remove markdown headers, lists, and other non-code wrappers."""
        lines = content.split("\n")

        # Remove leading/trailing markdown headers
        while lines and lines[0].startswith("#"):
            lines.pop(0)
        while lines and lines[-1].startswith("#"):
            lines.pop()

        # Remove common wrapper text
        wrapper_phrases = [
            "here is the",
            "here's the",
            "here is your",
            "here's your",
            "generated code:",
            "the code:",
            "```file",
            "```output",
            "```result",
        ]

        # Remove first line if it's a wrapper phrase
        if lines:
            first_line = lines[0].lower().strip()
            for phrase in wrapper_phrases:
                if phrase in first_line:
                    lines.pop(0)
                    break

        return "\n".join(lines)

    def _strip_whitespace(self, content: str) -> str:
        """Strip unnecessary whitespace while preserving structure."""
        lines = content.split("\n")

        # Find minimum indentation (excluding empty lines)
        min_indent = None
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if min_indent is None or indent < min_indent:
                    min_indent = indent

        # Remove common indentation
        if min_indent and min_indent > 0:
            lines = [
                line[min_indent:] if line.startswith(" " * min_indent) else line
                for line in lines
            ]

        # Remove leading empty lines
        while lines and not lines[0].strip():
            lines.pop(0)

        # Remove trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()

        return "\n".join(lines)

    def extract_language(self, content: str) -> Optional[str]:
        """Extract detected programming language from content."""
        language_patterns = {
            "python": [r"^import\s+", r"^from\s+\w+\s+import", r"^def\s+\w+\(", r"^class\s+\w+:"],
            "typescript": [r"^import\s+.*\s+from\s+['\"]", r"^export\s+", r":\s*(string|number|boolean|any)\b"],
            "javascript": [r"^const\s+\w+\s*=", r"^let\s+\w+\s*=", r"^function\s+\w+\("],
            "rust": [r"^use\s+\w+::", r"^fn\s+\w+\(", r"^struct\s+\w+", r"^impl\s+\w+"],
            "go": [r"^package\s+\w+", r"^func\s+\w+\(", r"^type\s+\w+\s+struct"],
            "java": [r"^public\s+(class|interface|enum)", r"^package\s+\w+;", r"^import\s+\w+;"],
            "sql": [r"^SELECT\s+", r"^INSERT\s+", r"^UPDATE\s+", r"^CREATE\s+(TABLE|DATABASE|INDEX)"],
            "yaml": [r"^\w+:\s*$", r"^\w+:\s+\S", r"^\s*-\s+\w+"],
            "json": [r"^\s*\{", r"^\s*\["],
        }

        for lang, patterns in language_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE):
                    return lang

        return None


class ContentValidator:
    """Validates generated content meets quality standards.

    Performs multiple validation checks to ensure content is:
    - Not empty
    - Not a placeholder
    - Matches expected language
    - Has acceptable complexity
    - Contains no forbidden patterns
    """

    # Forbidden patterns that indicate placeholder/invalid content
    # These reject stub/scaffold content while allowing legitimate syntax
    FORBIDDEN_PATTERNS = [
        r"^\s*TODO\s*$",  # Line with only TODO
        r"^\s*FIXME\s*$",  # Line with only FIXME
        r"^\s*PLACEHOLDER\s*$",  # Line with only PLACEHOLDER
        r"^\s*INSERT\s+CODE\s+HERE\s*$",  # Explicit placeholder instruction
        r"^\s*NOT\s+IMPLEMENTED\s*$",  # Explicit not implemented marker
        r"^\s*\{\{\s*\}\}\s*$",  # Empty template variable
        r"^\s*#\s*(TODO|FIXME|PLACEHOLDER)\s*$",  # Comment-only TODO/FIXME
        r"^\s*//\s*(TODO|FIXME|PLACEHOLDER)\s*$",  # JS comment-only TODO/FIXME
        r"^\s*/\*\s*(TODO|FIXME|PLACEHOLDER)\s*\*/\s*$",  # Single-line block comment stub
    ]

    def __init__(self, min_lines: int = 1, strict: bool = False):
        """Initialize the content validator.

        Args:
            min_lines: Minimum non-empty lines required
            strict: If True, fail on any warning
        """
        self.min_lines = min_lines
        self.strict = strict
        self._forbidden_re = [
            re.compile(p, re.MULTILINE | re.IGNORECASE)
            for p in self.FORBIDDEN_PATTERNS
        ]

    def validate(
        self,
        content: str,
        unit: ArtifactExecutionUnit,
    ) -> ContentValidationResult:
        """Validate generated content.

        Args:
            content: Generated content to validate
            unit: Source artifact execution unit

        Returns:
            ContentValidationResult with all check results
        """
        checks: List[ContentValidationCheck] = []
        errors: List[str] = []
        warnings: List[str] = []

        # Check 1: Content not empty
        passed, msg = validate_content_not_empty(content, self.min_lines)
        checks.append(ContentValidationCheck(
            check_id=f"check-{unit.artifact_execution_id}-not-empty",
            check_type="not_empty",
            passed=passed,
            message=msg,
        ))
        if not passed:
            errors.append(msg)

        # Check 2: No placeholders
        passed, msg = validate_content_no_placeholders(content)
        checks.append(ContentValidationCheck(
            check_id=f"check-{unit.artifact_execution_id}-no-placeholders",
            check_type="no_placeholders",
            passed=passed,
            message=msg,
        ))
        if not passed:
            errors.append(msg)

        # Check 3: Language match
        if unit.language:
            passed, msg = validate_language_match(content, unit.language)
            checks.append(ContentValidationCheck(
                check_id=f"check-{unit.artifact_execution_id}-language",
                check_type="language_match",
                passed=passed,
                message=msg,
            ))
            if not passed:
                errors.append(msg)

        # Check 4: No forbidden patterns
        for i, pattern_re in enumerate(self._forbidden_re):
            if pattern_re.search(content):
                msg = f"Content matches forbidden pattern {i+1}"
                checks.append(ContentValidationCheck(
                    check_id=f"check-{unit.artifact_execution_id}-forbidden-{i}",
                    check_type="forbidden_pattern",
                    passed=False,
                    message=msg,
                ))
                errors.append(msg)
                break

        # Check 5: Line count sanity
        line_count = len([l for l in content.split("\n") if l.strip()])
        if line_count < self.min_lines:
            msg = f"Content has {line_count} lines, minimum is {self.min_lines}"
            checks.append(ContentValidationCheck(
                check_id=f"check-{unit.artifact_execution_id}-line-count",
                check_type="line_count",
                passed=False,
                message=msg,
            ))
            errors.append(msg)
        else:
            checks.append(ContentValidationCheck(
                check_id=f"check-{unit.artifact_execution_id}-line-count",
                check_type="line_count",
                passed=True,
                message=f"Content has {line_count} lines",
            ))

        # Check 6: Valid UTF-8
        try:
            content.encode("utf-8").decode("utf-8")
            checks.append(ContentValidationCheck(
                check_id=f"check-{unit.artifact_execution_id}-utf8",
                check_type="utf8_encoding",
                passed=True,
                message="Content is valid UTF-8",
            ))
        except UnicodeError as e:
            checks.append(ContentValidationCheck(
                check_id=f"check-{unit.artifact_execution_id}-utf8",
                check_type="utf8_encoding",
                passed=False,
                message=f"Invalid UTF-8 encoding: {e}",
            ))
            errors.append(str(e))

        # Determine overall pass
        passed = len(errors) == 0 and (not self.strict or len(warnings) == 0)

        validation_id = f"val-{unit.artifact_execution_id}"

        return ContentValidationResult(
            validation_id=validation_id,
            artifact_execution_id=unit.artifact_execution_id,
            passed=passed,
            checks=tuple(checks),
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def validate_with_result(
        self,
        content: str,
        unit: ArtifactExecutionUnit,
        strategy: GenerationStrategy,
    ) -> GeneratedContent:
        """Validate content and create GeneratedContent.

        Args:
            content: Generated content to validate
            unit: Source artifact execution unit
            strategy: Generation strategy used

        Returns:
            GeneratedContent with validation results
        """
        validation = self.validate(content, unit)

        # Compute content hash
        content_hash = compute_content_hash(content)

        # Count lines
        line_count = len([l for l in content.split("\n") if l.strip()])

        content_id = f"genc-{unit.artifact_execution_id}"

        return GeneratedContent(
            content_id=content_id,
            artifact_execution_id=unit.artifact_execution_id,
            content=content,
            source=strategy.value,
            strategy=strategy,
            language=unit.language,
            file_format=unit.file_format,
            line_count=line_count,
            validation_passed=validation.passed,
            validation_errors=validation.errors,
            deterministic_hash=content_hash,
        )


def create_generated_content(
    content: str,
    unit: ArtifactExecutionUnit,
    strategy: GenerationStrategy,
    validation_passed: bool = True,
) -> GeneratedContent:
    """Helper to create GeneratedContent from raw content.

    Args:
        content: Generated content
        unit: Source artifact execution unit
        strategy: Generation strategy used
        validation_passed: Whether validation passed

    Returns:
        GeneratedContent object
    """
    content_hash = compute_content_hash(content)
    line_count = len([l for l in content.split("\n") if l.strip()])

    content_id = f"genc-{unit.artifact_execution_id}"

    return GeneratedContent(
        content_id=content_id,
        artifact_execution_id=unit.artifact_execution_id,
        content=content,
        source=strategy.value,
        strategy=strategy,
        language=unit.language,
        file_format=unit.file_format,
        line_count=line_count,
        validation_passed=validation_passed,
        validation_errors=(),
        deterministic_hash=content_hash,
    )
