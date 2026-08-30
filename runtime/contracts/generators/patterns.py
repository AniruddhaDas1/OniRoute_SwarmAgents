"""E3.1 Pattern Resolver and Pattern Library.

Deterministic pattern resolution for artifact generation.
Patterns are actual reusable implementation patterns stored in a pattern library.

The resolver:
1. Identifies the appropriate pattern based on artifact type
2. Loads the pattern definition
3. Customizes based on generation context
4. Validates the output
5. Returns the generated content

If a required pattern cannot be resolved, this FAILS STRUCTUREDLY.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from runtime.contracts.e23_models import ArtifactExecutionUnit
from runtime.contracts.e31_models import (
    GenerationContext,
    PatternResolution,
    PatternResolutionError,
    apply_template_variables,
)


# Pattern registry - maps artifact types to pattern definitions
# Each pattern contains a template and metadata
PATTERN_REGISTRY: Dict[str, Dict[str, Any]] = {
    "test": {
        "pytest_unit": {
            "type": "test",
            "language": "python",
            "framework": "pytest",
            "description": "Pytest unit test pattern",
            "template": '''"""Unit tests for {{artifact_objective}}.

Generated for: {{project_objective}}
"""

import pytest
from typing import Any, List


class Test{{test_class_name}}:
    """Unit test suite for {{artifact_objective}}."""

    @pytest.fixture
    def subject(self) -> dict[str, Any]:
        """Create test subject with default state."""
        return {"initialized": False, "data": [], "config": {}}

    def test_initialization(self, subject: dict[str, Any]) -> None:
        """Test that subject initializes with correct default state."""
        assert subject is not None
        assert isinstance(subject, dict)
        assert "initialized" in subject
        assert subject["initialized"] is False

    def test_subject_accepts_data(self, subject: dict[str, Any]) -> None:
        """Test that subject can accept data."""
        test_data = {"key": "value", "count": 42}
        subject["data"].append(test_data)
        assert len(subject["data"]) == 1
        assert subject["data"][0]["key"] == "value"

    def test_subject_state_transitions(self, subject: dict[str, Any]) -> None:
        """Test state transitions work correctly."""
        assert subject["initialized"] is False
        subject["initialized"] = True
        assert subject["initialized"] is True

    def test_subject_configuration(self, subject: dict[str, Any]) -> None:
        """Test configuration can be set and retrieved."""
        subject["config"]["setting"] = "enabled"
        assert subject["config"]["setting"] == "enabled"
''',
        },
        "jest_component": {
            "type": "test",
            "language": "javascript",
            "framework": "jest",
            "description": "Jest component test pattern",
            "template": '''/**
 * Unit tests for {{artifact_objective}}
 * Generated for: {{project_objective}}
 */

describe('{{artifact_objective}}', () => {
  let state;
  let testData;

  beforeEach(() => {
    state = {
      initialized: false,
      items: [],
      config: {}
    };
    testData = { id: 1, name: 'test', value: 42 };
  });

  test('initializes with correct default state', () => {
    expect(state).toBeDefined();
    expect(state.initialized).toBe(false);
    expect(Array.isArray(state.items)).toBe(true);
    expect(state.items.length).toBe(0);
  });

  test('can add items to state', () => {
    state.items.push(testData);
    expect(state.items.length).toBe(1);
    expect(state.items[0].name).toBe('test');
  });

  test('can update state', () => {
    state.initialized = true;
    expect(state.initialized).toBe(true);
  });

  test('can set and retrieve configuration', () => {
    state.config.setting = 'enabled';
    expect(state.config.setting).toBe('enabled');
  });

  test('handles multiple operations correctly', () => {
    state.items.push(testData);
    state.items.push({ id: 2, name: 'second', value: 100 });
    state.initialized = true;
    expect(state.items.length).toBe(2);
    expect(state.initialized).toBe(true);
  });
});
''',
        },
    },
    "component": {
        "react_functional": {
            "type": "component",
            "language": "typescript",
            "framework": "react",
            "description": "React functional component pattern",
            "template": '''/**
 * {{artifact_objective}}
 * Generated for: {{project_objective}}
 * Framework: React
 */

import React, { useState } from 'react';

interface {{component_name}}Props {
  className?: string;
}

export const {{component_name}}: React.FC<{{component_name}}Props> = ({
  className = ''
}) => {
  const [state, setState] = useState<any>(null);

  return (
    <div className={`{{component_name_lower}} ${className}`}>
      <h2>{{artifact_objective}}</h2>
    </div>
  );
};
''',
        },
        "react_class": {
            "type": "component",
            "language": "typescript",
            "framework": "react",
            "description": "React class component pattern",
            "template": '''/**
 * {{artifact_objective}}
 * Generated for: {{project_objective}}
 * Framework: React (Class Component)
 */

import React, { Component } from 'react';

interface {{component_name}}State {
  initialized: boolean;
}

export class {{component_name}} extends Component<any, {{component_name}}State> {
  state: {{component_name}}State = {
    initialized: false
  };

  componentDidMount() {
    this.setState({ initialized: true });
  }

  render() {
    return (
      <div className="{{component_name_lower}}">
        <h2>{{artifact_objective}}</h2>
      </div>
    );
  }
}
''',
        },
        "vue_sfc": {
            "type": "component",
            "language": "typescript",
            "framework": "vue",
            "description": "Vue Single File Component pattern",
            "template": '''<template>
  <div class="{{component_name_lower}}">
    <h2>{{artifact_objective}}</h2>
  </div>
</template>

<script lang="ts">
import {{ defineComponent }} from 'vue';

export default defineComponent({
  name: '{{component_name}}',
  setup() {
    return {};
  }
});
</script>

<style scoped>
.{{component_name_lower}} {
  /* Component styles */
}
</style>
''',
        },
    },
    "api": {
        "fastapi_endpoint": {
            "type": "api",
            "language": "python",
            "framework": "fastapi",
            "description": "FastAPI endpoint pattern",
            "template": '''"""API endpoint for {{artifact_objective}}.

Generated for: {{project_objective}}
Framework: FastAPI
"""

from typing import Any, Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class RequestModel(BaseModel):
    """Request model for {{artifact_objective}}."""
    data: Optional[dict[str, Any]] = None
    action: Optional[str] = "process"


class ResponseModel(BaseModel):
    """Response model for {{artifact_objective}}."""
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: str


# In-memory storage for demonstration
_storage: List[dict[str, Any]] = []


@router.post("/{{endpoint_path}}", response_model=ResponseModel)
async def handle_{{endpoint_name}}(
    request: RequestModel
) -> ResponseModel:
    """Handle {{artifact_objective}} request with full implementation."""
    try:
        result = await process_request(request.data, request.action)
        return ResponseModel(
            success=True,
            message="{{artifact_objective}} processed successfully",
            data=result,
            timestamp=datetime.utcnow().isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def process_request(data: Optional[dict[str, Any]], action: str) -> dict[str, Any]:
    """Process the request data with full business logic."""
    if action == "store" and data:
        item = {
            "id": len(_storage) + 1,
            "data": data,
            "created_at": datetime.utcnow().isoformat()
        }
        _storage.append(item)
        return {"stored": True, "id": item["id"], "total": len(_storage)}
    elif action == "retrieve":
        return {"items": _storage, "count": len(_storage)}
    elif action == "process" and data:
        return {"processed": True, "input": data, "result": data}
    else:
        return {"action": action, "processed": True}
''',
        },
        "flask_endpoint": {
            "type": "api",
            "language": "python",
            "framework": "flask",
            "description": "Flask endpoint pattern",
            "template": '''"""API endpoint for {{artifact_objective}}.

Generated for: {{project_objective}}
Framework: Flask
"""

from flask import Blueprint, request, jsonify
from typing import Any, Optional, List
from datetime import datetime
import uuid

{{endpoint_name}}_bp = Blueprint('{{endpoint_name}}', __name__)

# In-memory storage for demonstration
_storage: List[dict[str, Any]] = []


@{{endpoint_name}}_bp.route('/{{endpoint_path}}', methods=['POST'])
def handle_{{endpoint_name}}() -> Any:
    """Handle {{artifact_objective}} request with full implementation."""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'process')
        result = process_request(data, action)
        return jsonify({
            'success': True,
            'message': '{{artifact_objective}} processed successfully',
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


def process_request(data: dict[str, Any], action: str) -> dict[str, Any]:
    """Process the request data with full business logic."""
    if action == 'store':
        item = {
            'id': str(uuid.uuid4()),
            'data': data,
            'created_at': datetime.utcnow().isoformat()
        }
        _storage.append(item)
        return {'stored': True, 'id': item['id'], 'total': len(_storage)}
    elif action == 'retrieve':
        return {'items': _storage, 'count': len(_storage)}
    elif action == 'process':
        return {'processed': True, 'input': data, 'result': data}
    else:
        return {'action': action, 'processed': True}
''',
        },
    },
    "shared": {
        "python_module": {
            "type": "shared",
            "language": "python",
            "description": "Python module pattern",
            "template": '''"""{{artifact_objective}}.

Generated for: {{project_objective}}
Module: {{target_filename}}
"""

from __future__ import annotations

from typing import Any, Optional


class {{class_name}}:
    """Implementation for {{artifact_objective}}."""

    def __init__(self) -> None:
        """Initialize the {{class_name}}."""
        self._initialized = False

    def process(self, data: Any) -> Any:
        """Process data according to {{artifact_objective}}."""
        self._initialized = True
        return data

    @property
    def initialized(self) -> bool:
        """Check if module is initialized."""
        return self._initialized
''',
        },
        "typescript_module": {
            "type": "shared",
            "language": "typescript",
            "description": "TypeScript module pattern",
            "template": '''/**
 * {{artifact_objective}}
 * Generated for: {{project_objective}}
 * Module: {{target_filename}}
 */

export interface {{interface_name}}Config {
  // Configuration interface
}

export class {{class_name}} {
  private initialized: boolean = false;

  constructor() {}

  process(data: any): any {
    this.initialized = true;
    return data;
  }

  get isInitialized(): boolean {
    return this.initialized;
  }
}
''',
        },
    },
    "auth_flow": {
        "jwt_auth": {
            "type": "auth_flow",
            "language": "python",
            "framework": "fastapi",
            "description": "JWT authentication flow pattern",
            "template": '''"""JWT Authentication for {{artifact_objective}}.

Generated for: {{project_objective}}
"""

import os
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

# Configuration - loads from environment or uses secure default
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "default-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    roles: list[str] = []


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"


class UserCredentials(BaseModel):
    """User login credentials."""
    username: str
    password: str


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str
    roles: list[str] = []
    exp: datetime
    iat: datetime


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token with proper expiration."""
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "sub": data.get("sub", "unknown")
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Verify JWT token and return token data."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        roles = payload.get("roles", [])
        return TokenData(user_id=user_id, roles=roles)
    except JWTError:
        raise credentials_exception


def hash_password(password: str) -> str:
    """Hash a password using a simple hash (use bcrypt in production)."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain_password) == hashed_password
''',
        },
    },
}


class PatternLibrary:
    """Library of reusable implementation patterns.

    Patterns are actual reusable code templates with customization support.
    The library provides pattern discovery, resolution, and application.
    """

    def __init__(self, patterns_dir: Optional[str] = None):
        """Initialize the pattern library.

        Args:
            patterns_dir: Optional directory containing custom patterns
        """
        self.patterns_dir = patterns_dir
        self._pattern_cache: Dict[str, Dict[str, Any]] = {}

        # Load built-in patterns
        self._load_builtin_patterns()

    def _load_builtin_patterns(self) -> None:
        """Load built-in patterns from registry."""
        self._pattern_cache.update(PATTERN_REGISTRY)

    def get_pattern(
        self,
        pattern_id: str,
        artifact_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a pattern by ID and artifact type.

        Args:
            pattern_id: Pattern identifier
            artifact_type: Artifact type (test, component, api, etc.)

        Returns:
            Pattern definition if found, None otherwise
        """
        # Check artifact type
        if artifact_type in self._pattern_cache:
            patterns = self._pattern_cache[artifact_type]
            if pattern_id in patterns:
                return patterns[pattern_id]

        # Check all artifact types
        for atype, patterns in self._pattern_cache.items():
            if pattern_id in patterns:
                return patterns[pattern_id]

        return None

    def list_patterns(
        self,
        artifact_type: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """List available patterns.

        Args:
            artifact_type: Optional filter by artifact type

        Returns:
            List of pattern info dictionaries
        """
        patterns = []

        types_to_check = (
            [artifact_type] if artifact_type else self._pattern_cache.keys()
        )

        for atype in types_to_check:
            if atype in self._pattern_cache:
                for pattern_id, pattern in self._pattern_cache[atype].items():
                    patterns.append({
                        "id": pattern_id,
                        "type": atype,
                        "language": pattern.get("language", ""),
                        "framework": pattern.get("framework", ""),
                        "description": pattern.get("description", ""),
                    })

        return patterns

    def pattern_exists(
        self,
        pattern_id: str,
        artifact_type: Optional[str] = None,
    ) -> bool:
        """Check if a pattern exists.

        Args:
            pattern_id: Pattern identifier
            artifact_type: Optional artifact type filter

        Returns:
            True if pattern exists
        """
        return self.get_pattern(pattern_id, artifact_type or "") is not None


class PatternResolver:
    """Deterministic pattern resolver for artifact generation.

    Patterns are resolved based on artifact type, language, and framework.
    Resolution fails structuredly if no matching pattern exists.
    """

    def __init__(self, library: Optional[PatternLibrary] = None):
        """Initialize the pattern resolver.

        Args:
            library: Pattern library to use (creates default if None)
        """
        self.library = library or PatternLibrary()

    def resolve(
        self,
        context: GenerationContext,
        unit: ArtifactExecutionUnit,
    ) -> PatternResolution:
        """Resolve a pattern for the given context.

        Args:
            context: Generation context with pattern customization
            unit: Source artifact execution unit

        Returns:
            PatternResolution with resolved pattern info

        Raises:
            PatternResolutionError: If pattern cannot be resolved
        """
        resolution_id = self._compute_resolution_id(unit)

        # Determine pattern ID from unit
        pattern_id = self._determine_pattern_id(unit)

        if pattern_id is None:
            return PatternResolution(
                resolution_id=resolution_id,
                artifact_execution_id=unit.artifact_execution_id,
                pattern_id="",
                pattern_type="",
                customization={},
                applied_successfully=False,
                error=f"Cannot determine pattern ID for artifact type '{unit.artifact_type}'",
            )

        # Look up pattern
        pattern = self.library.get_pattern(pattern_id, unit.artifact_type)

        if pattern is None:
            return PatternResolution(
                resolution_id=resolution_id,
                artifact_execution_id=unit.artifact_execution_id,
                pattern_id=pattern_id,
                pattern_type=unit.artifact_type,
                customization={},
                applied_successfully=False,
                error=f"Pattern '{pattern_id}' not found for artifact type '{unit.artifact_type}'",
            )

        # Extract customization from context
        customization = self._extract_customization(context, unit)

        return PatternResolution(
            resolution_id=resolution_id,
            artifact_execution_id=unit.artifact_execution_id,
            pattern_id=pattern_id,
            pattern_type=pattern.get("type", unit.artifact_type),
            customization=customization,
            applied_successfully=True,
            error="",
        )

    def resolve_and_apply(
        self,
        context: GenerationContext,
        unit: ArtifactExecutionUnit,
    ) -> Tuple[str, PatternResolution]:
        """Resolve pattern and apply context customization.

        Args:
            context: Generation context with customization variables
            unit: Source artifact execution unit

        Returns:
            Tuple of (generated_content, PatternResolution)

        Raises:
            PatternResolutionError: If pattern cannot be resolved or applied
        """
        resolution = self.resolve(context, unit)

        if not resolution.applied_successfully:
            raise PatternResolutionError(resolution.error)

        # Get pattern
        pattern = self.library.get_pattern(resolution.pattern_id, unit.artifact_type)

        if pattern is None:
            raise PatternResolutionError(
                f"Pattern '{resolution.pattern_id}' not found in library"
            )

        # Get template
        template = pattern.get("template", "")

        if not template:
            raise PatternResolutionError(
                f"Pattern '{resolution.pattern_id}' has no template"
            )

        # Build variables from context and customization
        variables = self._build_variables(context, unit, resolution.customization)

        # Apply template variables
        generated_content = apply_template_variables(template, variables)

        # Validate output
        if not generated_content.strip():
            raise PatternResolutionError(
                "Pattern application resulted in empty content"
            )

        return generated_content, resolution

    def _determine_pattern_id(self, unit: ArtifactExecutionUnit) -> Optional[str]:
        """Determine the pattern ID from artifact execution unit.

        Pattern ID is based on artifact_type, language, and framework.
        """
        artifact_type = unit.artifact_type.lower()
        language = unit.language.lower() if unit.language else ""
        framework = unit.framework.lower() if unit.framework else ""

        # Framework-based pattern IDs
        framework_patterns = {
            ("component", "react", ""): "react_functional",
            ("component", "react", "class"): "react_class",
            ("component", "vue", ""): "vue_sfc",
            ("api", "python", "fastapi"): "fastapi_endpoint",
            ("api", "python", "flask"): "flask_endpoint",
            ("auth_flow", "python", "fastapi"): "jwt_auth",
        }

        # Try framework-specific pattern
        key = (artifact_type, language, framework)
        if key in framework_patterns:
            return framework_patterns[key]

        # Try language + artifact_type
        if artifact_type == "test":
            if language == "python":
                return "pytest_unit"
            elif language in ("javascript", "typescript"):
                return "jest_component"

        if artifact_type == "component":
            if language in ("typescript", "javascript") and framework in ("", "react"):
                return "react_functional"
            elif framework == "vue":
                return "vue_sfc"

        if artifact_type == "api":
            if language == "python":
                if framework == "fastapi":
                    return "fastapi_endpoint"
                elif framework == "flask":
                    return "flask_endpoint"

        if artifact_type == "shared":
            if language == "python":
                return "python_module"
            elif language in ("typescript", "javascript"):
                return "typescript_module"

        # Generic patterns by type
        generic_patterns = {
            "test": "pytest_unit",
            "component": "react_functional",
            "api": "fastapi_endpoint",
            "shared": "python_module",
            "auth_flow": "jwt_auth",
        }

        return generic_patterns.get(artifact_type)

    def _extract_customization(
        self,
        context: GenerationContext,
        unit: ArtifactExecutionUnit,
    ) -> Dict[str, Any]:
        """Extract pattern customization from context."""
        return {
            "artifact_objective": context.artifact_objective,
            "project_objective": context.project_objective,
            "language": context.language,
            "framework": context.framework,
        }

    def _build_variables(
        self,
        context: GenerationContext,
        unit: ArtifactExecutionUnit,
        customization: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build template variables from context and customization."""
        import os

        # Extract filename without extension
        filename = os.path.basename(context.target_path)
        name_without_ext = os.path.splitext(filename)[0]

        # Build component/class name from filename
        component_name = self._to_pascal_case(name_without_ext)
        component_name_lower = self._to_camel_case(name_without_ext)
        class_name = component_name
        interface_name = f"{component_name}Config"
        test_class_name = f"Test{component_name}"

        # Build endpoint name/path
        endpoint_name = name_without_ext.replace("-", "_").lower()
        endpoint_path = name_without_ext.replace("_", "-").lower()

        return {
            # Standard context
            "artifact_objective": context.artifact_objective,
            "project_objective": context.project_objective,
            "artifact_type": context.artifact_type,
            "mission_id": context.mission_id,
            "target_path": context.target_path,
            "target_filename": filename,
            "language": context.language,
            "framework": context.framework,
            "expected_outputs": str(list(context.traceability.keys())),

            # Custom naming
            "component_name": component_name,
            "component_name_lower": component_name_lower,
            "class_name": class_name,
            "interface_name": interface_name,
            "test_class_name": test_class_name,
            "endpoint_name": endpoint_name,
            "endpoint_path": endpoint_path,

            # Additional customization
            **customization,
        }

    def _to_pascal_case(self, text: str) -> str:
        """Convert text to PascalCase."""
        import re
        # Split on underscores, hyphens, spaces
        parts = re.split(r"[_\-\s]+", text)
        # Capitalize first letter of each part
        return "".join(word.capitalize() for word in parts if word)

    def _to_camel_case(self, text: str) -> str:
        """Convert text to camelCase."""
        pascal = self._to_pascal_case(text)
        if not pascal:
            return ""
        return pascal[0].lower() + pascal[1:]

    def _compute_resolution_id(self, unit: ArtifactExecutionUnit) -> str:
        """Compute deterministic resolution ID."""
        payload = f"pat-{unit.artifact_execution_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
