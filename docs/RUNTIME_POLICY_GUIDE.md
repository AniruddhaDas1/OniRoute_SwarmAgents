# Declarative Runtime Review Policy Guide (ACR-006 Phase R5)

This guide documents the **Declarative Runtime Review Policy** architecture introduced in ACR-006 Phase R5.

---

## 1. Overview & Architectural Goals

In ACR-006 Phase R4, review eligibility was evaluated against a hardcoded set of artifact types (`{"review", "schema", "config", "binary"}`).

In Phase R5, hardcoded review logic was eliminated. `RuntimeReviewEngine` now consumes a declarative `ReviewPolicy` contract.

**Key Design Goals:**
- **Zero hardcoding:** Review rules are fully configurable.
- **Protocol contract:** Any class implementing `ReviewPolicy` protocol can drive review gates.
- **Default backwards compatibility:** `DefaultReviewPolicy` preserves R4 behavior out of the box.
- **Rule-based policy support:** `RuleBasedReviewPolicy` allows constructing policies dynamically from declarative rules.

---

## 2. Policy Contract Specification

```python
from typing import Protocol, runtime_checkable
from runtime.agent.models import ArtifactRecord

@runtime_checkable
class ReviewPolicy(Protocol):
    """Contract that all review policies must satisfy."""

    def requires_review(self, artifact: ArtifactRecord) -> bool:
        """Return True if artifact requires human review."""
        ...

    def policy_name(self) -> str:
        """Return canonical policy name for telemetry and reports."""
        ...

    def policy_description(self) -> str:
        """Return human-readable policy description."""
        ...
```

---

## 3. Built-in Policy Implementations

### 1. `DefaultReviewPolicy`
Preserves Phase R4 behavior.
- **Review Required:** `review`, `schema`, `config`, `binary`
- **Auto-Approved:** `code`, `documentation`, `test_suite`, `report`, `data`, `custom`

### 2. `StrictReviewPolicy`
Requires human approval for **ALL** artifacts regardless of category. Useful for high-security environments.

### 3. `PermissiveReviewPolicy`
Auto-approves **ALL** artifacts. Intended for development and automated testing environments.

### 4. Preset Declarative Policies
- **`SECURITY_POLICY`**: Review required for `schema`, `config`, `binary`, `review`. Auto-approved for docs and reports.
- **`INFRASTRUCTURE_POLICY`**: Review required for `config`, `binary`, `schema`, `code`. Auto-approved for docs.
- **`DEPLOYMENT_POLICY`**: Full sign-off policy requiring review for all artifacts before deployment.

---

## 4. Creating Custom Declarative Policies

You can instantiate a `RuleBasedReviewPolicy` with custom `ReviewRule` objects:

```python
from runtime.agent.recovery.policy import RuleBasedReviewPolicy, ReviewRule

custom_policy = RuleBasedReviewPolicy(
    rules=[
        ReviewRule(
            artifact_types=["schema", "config"],
            requires_review=True,
            reason="Database and config changes require review.",
        ),
        ReviewRule(
            artifact_types=["documentation"],
            requires_review=False,
            reason="Documentation updates do not require review.",
        ),
    ],
    default_requires_review=False,
    name="custom_engineering",
    description="Custom engineering review policy",
)

# Inject into RuntimeReviewEngine
from runtime.agent.recovery import RuntimeReviewEngine

engine = RuntimeReviewEngine(policy=custom_policy)
```

---

## 5. Integrating Policies in CLI Commands

Use the `--policy` option with `oniroute review`:

```bash
# Evaluate review under security policy
oniroute review sess-backend-001 --approve --policy security

# Evaluate review under strict policy
oniroute review sess-backend-001 --approve --policy strict
```
