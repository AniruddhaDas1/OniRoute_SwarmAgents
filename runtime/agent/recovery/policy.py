"""Declarative Runtime Review Policy for the OniRoute Recovery Engine (ACR-006 Phase R5).

Provides the ``ReviewPolicy`` protocol (contract) and built-in policy implementations:

- ``DefaultReviewPolicy``  — preserves R4 behavior (review for schema, config, binary, review types)
- ``StrictReviewPolicy``   — review required for all artifact types
- ``PermissiveReviewPolicy`` — review never required (useful for tests / dev environments)
- ``RuleBasedReviewPolicy``  — fully declarative, driven by a rule table

``RuntimeReviewEngine`` consumes a ``ReviewPolicy`` instance.
No review logic is hardcoded in the engine itself (R5 policy constraint).

Extension rule
--------------
To add a new policy, implement the ``ReviewPolicy`` protocol and pass an instance to
``RuntimeReviewEngine(policy=YourPolicy())``. No changes to the engine are required.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from runtime.agent.models import ArtifactRecord, ArtifactType


# ---------------------------------------------------------------------------
# ReviewPolicy Protocol (contract)
# ---------------------------------------------------------------------------

@runtime_checkable
class ReviewPolicy(Protocol):
    """Contract that all review policies must satisfy.

    A ``ReviewPolicy`` is a pure, stateless predicate: given an artifact, it
    returns True if human review is required before the session can proceed.

    Implementations MUST be deterministic (same input → same output) and
    MUST NOT perform I/O, AI calls, or state mutations.
    """

    def requires_review(self, artifact: ArtifactRecord) -> bool:
        """Return True if *artifact* requires human review.

        Parameters
        ----------
        artifact:
            The ArtifactRecord produced by an AgentSession.

        Returns
        -------
        bool
            True if human approval is required before the session may continue.
        """
        ...

    def policy_name(self) -> str:
        """Return the canonical name of this policy (for audit trails)."""
        ...

    def policy_description(self) -> str:
        """Return a human-readable description of the policy rules."""
        ...


# ---------------------------------------------------------------------------
# Built-in policy implementations
# ---------------------------------------------------------------------------

class DefaultReviewPolicy:
    """Preserves the Phase R4 behavior.

    Review is required for artifacts of type:
    - ``review``      — explicitly flagged for human review
    - ``schema``      — structural changes require approval
    - ``config``      — configuration changes are high risk
    - ``binary``      — opaque binary artifacts require sign-off

    Review is NOT required for:
    - ``code``, ``documentation``, ``test_suite``, ``report``, ``data``, ``custom``
    """

    _REVIEW_TYPES: frozenset[ArtifactType] = frozenset({
        ArtifactType.REVIEW,
        ArtifactType.SCHEMA,
        ArtifactType.CONFIG,
        ArtifactType.BINARY,
    })

    def requires_review(self, artifact: ArtifactRecord) -> bool:
        return artifact.artifact_type in self._REVIEW_TYPES

    def policy_name(self) -> str:
        return "default"

    def policy_description(self) -> str:
        return (
            "Review required for: review, schema, config, binary. "
            "Review not required for: code, documentation, test_suite, report, data, custom."
        )


class StrictReviewPolicy:
    """All artifacts require human review.

    Use in high-security or regulated environments where every output must
    be approved before the session may continue.
    """

    def requires_review(self, artifact: ArtifactRecord) -> bool:  # noqa: ARG002
        return True

    def policy_name(self) -> str:
        return "strict"

    def policy_description(self) -> str:
        return "Review required for ALL artifact types."


class PermissiveReviewPolicy:
    """No artifacts require human review.

    Use in development / testing environments where automatic approval is
    acceptable. NOT recommended for production use.
    """

    def requires_review(self, artifact: ArtifactRecord) -> bool:  # noqa: ARG002
        return False

    def policy_name(self) -> str:
        return "permissive"

    def policy_description(self) -> str:
        return "Review NOT required for any artifact type. Development use only."


# ---------------------------------------------------------------------------
# Declarative rule-based policy
# ---------------------------------------------------------------------------

class ReviewRule(BaseModel):
    """A single declarative review rule."""

    model_config = ConfigDict(frozen=True)

    artifact_types: list[str] = Field(
        ...,
        description="Artifact type values this rule applies to (e.g. ['schema', 'config']).",
    )
    requires_review: bool = Field(
        ...,
        description="True if matching artifacts require human review.",
    )
    reason: str = Field(
        default="",
        description="Human-readable rationale for this rule.",
    )


class RuleBasedReviewPolicy:
    """Fully declarative review policy driven by a list of ``ReviewRule`` objects.

    Rules are evaluated in order. The first matching rule wins.
    If no rule matches, ``default_requires_review`` is applied (default: False).

    Examples
    --------
    >>> policy = RuleBasedReviewPolicy(rules=[
    ...     ReviewRule(
    ...         artifact_types=["schema", "config", "binary"],
    ...         requires_review=True,
    ...         reason="Security-sensitive artifacts require approval.",
    ...     ),
    ...     ReviewRule(
    ...         artifact_types=["documentation"],
    ...         requires_review=False,
    ...         reason="Documentation does not require sign-off.",
    ...     ),
    ... ])
    >>> policy.requires_review(artifact)  # True if artifact_type is schema/config/binary
    """

    def __init__(
        self,
        rules: list[ReviewRule],
        default_requires_review: bool = False,
        name: str = "rule_based",
        description: str = "",
    ) -> None:
        self._rules = list(rules)
        self._default = default_requires_review
        self._name = name
        self._description = description or self._build_description()

    def requires_review(self, artifact: ArtifactRecord) -> bool:
        for rule in self._rules:
            if artifact.artifact_type.value in rule.artifact_types:
                return rule.requires_review
        return self._default

    def policy_name(self) -> str:
        return self._name

    def policy_description(self) -> str:
        return self._description

    def _build_description(self) -> str:
        parts = []
        for rule in self._rules:
        	parts.append(
                f"Types {rule.artifact_types} → {'review required' if rule.requires_review else 'no review'}"
                + (f" ({rule.reason})" if rule.reason else "")
            )
        default_str = "review required" if self._default else "no review"
        parts.append(f"Default → {default_str}")
        return "; ".join(parts)


# ---------------------------------------------------------------------------
# Standard policy catalog for common deployment scenarios
# ---------------------------------------------------------------------------

#: Standard policy: security + infrastructure always reviewed; docs optional.
SECURITY_POLICY = RuleBasedReviewPolicy(
    rules=[
        ReviewRule(
            artifact_types=["schema", "config", "binary"],
            requires_review=True,
            reason="Security-sensitive: schema, config, binary require approval.",
        ),
        ReviewRule(
            artifact_types=["review"],
            requires_review=True,
            reason="Explicitly flagged review artifacts always require approval.",
        ),
        ReviewRule(
            artifact_types=["documentation", "report", "data", "custom"],
            requires_review=False,
            reason="Low-risk artifacts do not require human review.",
        ),
    ],
    default_requires_review=False,
    name="security",
    description=(
        "Security policy: schema/config/binary/review require approval. "
        "Documentation, reports, data, and custom artifacts are auto-approved."
    ),
)

#: Infrastructure policy: all infrastructure-touching artifacts reviewed.
INFRASTRUCTURE_POLICY = RuleBasedReviewPolicy(
    rules=[
        ReviewRule(
            artifact_types=["config", "binary", "schema"],
            requires_review=True,
            reason="Infrastructure changes require approval.",
        ),
        ReviewRule(
            artifact_types=["code"],
            requires_review=True,
            reason="Code artifacts may affect deployment.",
        ),
    ],
    default_requires_review=False,
    name="infrastructure",
    description=(
        "Infrastructure policy: config, binary, schema, code require review. "
        "Documentation and reports are auto-approved."
    ),
)

#: Deployment policy: all artifacts reviewed (full sign-off required).
DEPLOYMENT_POLICY = RuleBasedReviewPolicy(
    rules=[
        ReviewRule(
            artifact_types=[t.value for t in ArtifactType],
            requires_review=True,
            reason="Deployment requires full sign-off on all artifacts.",
        ),
    ],
    default_requires_review=True,
    name="deployment",
    description="Deployment policy: ALL artifacts require human approval before deployment.",
)
