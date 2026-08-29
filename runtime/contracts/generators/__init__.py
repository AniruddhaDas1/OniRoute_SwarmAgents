"""E3.1 Real Code Generation Engine.

This package implements the Real Code Generation Engine (Phase E3.1) that consumes
ArtifactExecutionPlan and produces real source files through:

- Template resolution (TEMPLATE strategy)
- Pattern application (PATTERN strategy)
- LLM generation via existing InvocationEngine (LLM_GENERATED strategy)

Architecture:
    ArtifactExecutionPlan
        ↓
    ArtifactExecutionUnit
        ↓
    GenerationContext
        ↓
    TemplateResolver | PatternResolver | LLM Generation
        ↓
    GeneratedContent
        ↓
    ContentValidation
        ↓
    RepositoryWriter
        ↓
    REAL FILES
"""

from runtime.contracts.generators.context import GenerationContextBuilder, GenerationRequestConstructor
from runtime.contracts.generators.engine import (
    RealCodeGenerationEngine,
    get_invocation_engine,
    set_invocation_engine,
)
from runtime.contracts.generators.output import (
    ContentValidator,
    OutputNormalizer,
    create_generated_content,
)
from runtime.contracts.generators.patterns import (
    PatternLibrary,
    PatternResolver,
)
from runtime.contracts.generators.resolver import TemplateResolver
from runtime.contracts.generators.writer import (
    BlockingConflictDetector,
    RepositoryWriter,
)

__all__ = [
    # E3.1 Models (from e31_models.py)
    "BlockingConflict",
    "BlockingConflictReport",
    "CodeGenerationError",
    "ContentValidationCheck",
    "ContentValidationResult",
    "ContentValidationError",
    "GeneratedContent",
    "GenerationContext",
    "GenerationContextError",
    "GenerationReport",
    "GenerationRequest",
    "GenerationResult",
    "PatternResolution",
    "PatternResolutionError",
    "RepositoryWriteError",
    "RepositoryWriteResult",
    "TemplateResolution",
    "TemplateResolutionError",
    "WaveGenerationResult",
    # Core components
    "RealCodeGenerationEngine",
    "GenerationContextBuilder",
    "GenerationRequestConstructor",
    "ContentValidator",
    "OutputNormalizer",
    "PatternLibrary",
    "PatternResolver",
    "TemplateResolver",
    "RepositoryWriter",
    "BlockingConflictDetector",
    "create_generated_content",
    "get_invocation_engine",
    "set_invocation_engine",
]
