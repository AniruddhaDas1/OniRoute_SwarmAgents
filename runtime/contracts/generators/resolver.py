"""E3.1 Template Resolver.

Deterministic template resolution for artifact generation.
Templates are real artifacts stored in a clearly defined repository location.

The resolver:
1. Identifies the appropriate template based on artifact type
2. Loads the template content
3. Applies structured context variables
4. Validates the output
5. Returns the generated content

If no template exists, this FAILS STRUCTUREDLY.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from runtime.contracts.e23_models import ArtifactExecutionUnit, PathType
from runtime.contracts.e31_models import (
    GenerationContext,
    TemplateResolution,
    TemplateResolutionError,
    apply_template_variables,
    compute_generation_context_hash,
    extract_template_variables,
    validate_content_not_empty,
    validate_language_match,
    validate_target_path,
)


# Template registry - maps artifact types to template paths
# These are relative to the templates/ directory
TEMPLATE_REGISTRY: Dict[str, Dict[str, str]] = {
    "schema": {
        "database_schema": "templates/schema/database.sql",
        "api_schema": "templates/schema/openapi.yaml",
    },
    "config": {
        "json": "templates/config/config.json",
        "yaml": "templates/config/config.yaml",
        "env": "templates/config/config.env",
    },
    "test": {
        "pytest": "templates/test/python_pytest.py",
        "jest": "templates/test/javascript_jest.js",
        "unittest": "templates/test/python_unittest.py",
    },
    "component": {
        "react": "templates/component/react.tsx",
        "vue": "templates/component/vue.vue",
        "angular": "templates/component/angular.ts",
    },
    "api": {
        "rest": "templates/api/rest.py",
        "graphql": "templates/api/graphql.py",
    },
    "documentation": {
        "readme": "templates/docs/README.md",
        "api_doc": "templates/docs/API.md",
        "architecture": "templates/docs/ARCHITECTURE.md",
    },
}


# Default template for unknown types
DEFAULT_TEMPLATE_PATH = "templates/default/generic.txt"


class TemplateResolver:
    """Deterministic template resolver for artifact generation.

    Templates must be real files stored in the repository.
    Resolution fails structuredly if no matching template exists.
    """

    def __init__(self, repository_root: str):
        """Initialize the template resolver.

        Args:
            repository_root: Absolute path to repository root
        """
        self.repository_root = repository_root
        self.template_base = os.path.join(repository_root, "templates")

        # Cache for loaded templates
        self._template_cache: Dict[str, str] = {}

    def resolve(
        self,
        context: GenerationContext,
        unit: ArtifactExecutionUnit,
    ) -> TemplateResolution:
        """Resolve a template for the given context.

        Args:
            context: Generation context with template variables
            unit: Source artifact execution unit

        Returns:
            TemplateResolution with resolved template info

        Raises:
            TemplateResolutionError: If template cannot be resolved
        """
        resolution_id = self._compute_resolution_id(unit)

        # Determine template key from artifact type
        template_key = self._determine_template_key(unit)

        # Look up template path
        template_path = self._lookup_template_path(template_key, unit.artifact_type)

        if template_path is None:
            return TemplateResolution(
                resolution_id=resolution_id,
                artifact_execution_id=unit.artifact_execution_id,
                template_path="",
                template_type=template_key or "unknown",
                variables={},
                applied_successfully=False,
                error=f"No template found for artifact type '{unit.artifact_type}' with key '{template_key}'",
            )

        # Extract variables from context
        variables = extract_template_variables(context)

        return TemplateResolution(
            resolution_id=resolution_id,
            artifact_execution_id=unit.artifact_execution_id,
            template_path=template_path,
            template_type=template_key,
            variables=variables,
            applied_successfully=True,
            error="",
        )

    def resolve_and_apply(
        self,
        context: GenerationContext,
        unit: ArtifactExecutionUnit,
    ) -> Tuple[str, TemplateResolution]:
        """Resolve template and apply context variables.

        Args:
            context: Generation context with template variables
            unit: Source artifact execution unit

        Returns:
            Tuple of (generated_content, TemplateResolution)

        Raises:
            TemplateResolutionError: If template cannot be resolved or applied
        """
        resolution = self.resolve(context, unit)

        if not resolution.applied_successfully:
            raise TemplateResolutionError(resolution.error)

        # Load template content
        full_template_path = os.path.join(self.repository_root, resolution.template_path)

        if not os.path.exists(full_template_path):
            raise TemplateResolutionError(
                f"Template file not found: {full_template_path}"
            )

        with open(full_template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Apply variables
        generated_content = apply_template_variables(template_content, resolution.variables)

        # Validate output
        is_valid, error = validate_content_not_empty(generated_content)
        if not is_valid:
            raise TemplateResolutionError(f"Template application resulted in empty content: {error}")

        # Check language match if specified
        if context.language:
            is_valid, error = validate_language_match(generated_content, context.language)
            if not is_valid:
                raise TemplateResolutionError(f"Generated content language mismatch: {error}")

        return generated_content, resolution

    def _determine_template_key(self, unit: ArtifactExecutionUnit) -> str:
        """Determine the template key based on artifact execution unit.

        Template key is based on artifact_type and file_format/language.
        """
        artifact_type = unit.artifact_type.lower()
        file_format = unit.file_format.lower() if unit.file_format else ""
        language = unit.language.lower() if unit.language else ""
        framework = unit.framework.lower() if unit.framework else ""

        # Map framework to template key
        framework_to_key = {
            "react": "react",
            "vue": "vue",
            "angular": "angular",
            "pytest": "pytest",
            "jest": "jest",
            "unittest": "unittest",
            "rest": "rest",
            "graphql": "graphql",
            "database": "database_schema",
            "openapi": "api_schema",
        }

        # Try framework first
        if framework and framework in framework_to_key:
            return framework_to_key[framework]

        # Try language + format
        if language and file_format:
            key = f"{language}_{file_format}"
            if key in ["python_pytest", "javascript_jest", "python_unittest"]:
                return key.split("_")[1]  # Return pytest, jest, unittest

        # Try file format
        if file_format in ["json", "yaml", "env"]:
            return file_format

        # Fall back to artifact type
        return artifact_type

    def _lookup_template_path(self, template_key: str, artifact_type: str) -> Optional[str]:
        """Look up template path from registry.

        Args:
            template_key: Template key (e.g., 'react', 'pytest')
            artifact_type: Artifact type (e.g., 'component', 'test')

        Returns:
            Template path if found, None otherwise
        """
        # Check if artifact type exists in registry
        if artifact_type.lower() in TEMPLATE_REGISTRY:
            type_templates = TEMPLATE_REGISTRY[artifact_type.lower()]

            # Try exact match
            if template_key in type_templates:
                return type_templates[template_key]

            # Try artifact_type as fallback key
            if artifact_type.lower() in type_templates:
                return type_templates[artifact_type.lower()]

        # Check all types for the template key
        for atype, templates in TEMPLATE_REGISTRY.items():
            if template_key in templates:
                return templates[template_key]

        # No template found
        return None

    def _compute_resolution_id(self, unit: ArtifactExecutionUnit) -> str:
        """Compute deterministic resolution ID."""
        payload = f"tmpl-{unit.artifact_execution_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def get_available_templates(self) -> Dict[str, List[str]]:
        """Get all available templates grouped by type.

        Returns:
            Dictionary mapping artifact types to list of template keys
        """
        return {
            atype: list(templates.keys())
            for atype, templates in TEMPLATE_REGISTRY.items()
        }

    def template_exists(self, template_key: str, artifact_type: str) -> bool:
        """Check if a template exists for the given key and type.

        Args:
            template_key: Template key to check
            artifact_type: Artifact type to check

        Returns:
            True if template exists
        """
        return self._lookup_template_path(template_key, artifact_type) is not None


# ---------------------------------------------------------------------------
# Default template definitions (when templates directory doesn't exist)
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATES: Dict[str, str] = {
    "templates/schema/database.sql": """-- Database Schema for {{artifact_objective}}
-- Generated for: {{project_objective}}
-- Language: {{language}}

CREATE TABLE IF NOT EXISTS {{target_filename.replace('.sql', '')}} (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",
    "templates/config/config.json": """{
  "name": "{{artifact_objective}}",
  "description": "{{project_objective}}",
  "version": "1.0.0"
}
""",
    "templates/config/config.yaml": """---
# Configuration for {{artifact_objective}}
# Generated for: {{project_objective}}

name: {{artifact_objective}}
description: {{project_objective}}
version: "1.0.0"
""",
    "templates/test/python_pytest.py": '''"""Tests for {{artifact_objective}}.

Generated for: {{project_objective}}
"""

import pytest
from typing import Any


class Test{{target_filename.replace(".py", "").replace("_", "").title().replace(" ", "")}}:
    """Test suite for {{artifact_objective}}."""

    @pytest.fixture
    def setup(self) -> dict[str, Any]:
        """Set up test fixtures."""
        return {"objective": "{{artifact_objective}}"}

    def test_basic_functionality(self, setup: dict[str, Any]) -> None:
        """Test basic functionality."""
        assert setup["objective"] == "{{artifact_objective}}"

    def test_expected_outputs(self, setup: dict[str, Any]) -> None:
        """Test expected outputs are defined."""
        expected = {{expected_outputs}}
        assert isinstance(expected, list)
''',
    "templates/test/javascript_jest.js": '''/**
 * Tests for {{artifact_objective}}
 * Generated for: {{project_objective}}
 */

describe('{{artifact_objective}}', () => {
  const setup = {
    objective: '{{artifact_objective}}',
    expectedOutputs: {{expected_outputs}}
  };

  test('basic functionality', () => {
    expect(setup.objective).toBe('{{artifact_objective}}');
  });

  test('expected outputs defined', () => {
    expect(Array.isArray(setup.expectedOutputs)).toBe(true);
  });
});
''',
    "templates/component/react.tsx": '''/**
 * {{artifact_objective}}
 * Generated for: {{project_objective}}
 * Framework: React
 */

import React from 'react';

interface ComponentProps {
  // Define component props
}

export const {{target_filename.replace('.tsx', '').replace('.jsx', '') | capitalize}}: React.FC<ComponentProps> = (props) => {
  return (
    <div className="{{artifact_objective.replace(' ', '-').lower()}}">
      <h2>{{artifact_objective}}</h2>
    </div>
  );
};
''',
    "templates/api/rest.py": '''"""API endpoint for {{artifact_objective}}.

Generated for: {{project_objective}}
Framework: {{framework}}
"""

from typing import Any


async def handle_request(request: Any) -> dict[str, Any]:
    """Handle API request for {{artifact_objective}}."""
    return {
        "status": "success",
        "endpoint": "{{artifact_objective}}",
        "data": {}
    }
''',
    "templates/docs/README.md": '''# {{artifact_objective}}

{{project_objective}}

## Overview

This artifact implements: {{artifact_objective}}

## Details

- **Type**: {{artifact_type}}
- **Language**: {{language}}
- **Framework**: {{framework}}
- **Path**: `{{target_path}}`

## Generated Context

- Mission ID: {{mission_id}}
- Artifact Execution ID: {{artifact_execution_id}}
''',
}


def get_default_template_content(template_path: str) -> Optional[str]:
    """Get default template content if file doesn't exist.

    This allows the system to work without pre-existing template files,
    but generates deterministic content based on context.
    """
    return DEFAULT_TEMPLATES.get(template_path)
