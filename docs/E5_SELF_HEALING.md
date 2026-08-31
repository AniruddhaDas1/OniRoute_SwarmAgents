# E5 Self-Healing and Recovery Integration

## Phase E5 — Self-Healing and Recovery Engine for E4.x Pipeline

**Version:** v1.2.1
**Status:** Implemented
**Pipeline:** E4.x Review Pipeline → Recovery

---

## 1. Overview

E5 provides self-healing and recovery capabilities for the E4.x review pipeline. It integrates with the existing quality gate (E4.2) and release readiness (E4.3) stages to enable automated recovery when review findings are detected.

```
E3 Artifact Execution
    ↓
E4.1 ReviewReport
    ↓
E4.2 QualityGateResult
    ↓
E4.3 ReleaseReadinessResult
    ↓
E5 Recovery Assessment
    ↓
E5 Recovery Plan
    ↓
E5 Recovery Execution
    ↓
E4.1 Re-review (loop if needed)
```

---

## 2. Architecture Components

### E5.1 - Recovery Assessment Engine

Determines whether recovery is possible and eligible for a failed project.

**Key responsibilities:**
- Assess recovery eligibility from `ReleaseReadinessResult`
- Determine if findings are auto-repairable vs. manual
- Return `RecoveryEligibility` status

**Eligibility States:**
| Status | Description |
|--------|-------------|
| `NOT_NEEDED` | Project is ready, no recovery needed |
| `RECOVERABLE` | Issues can be automatically repaired |
| `NOT_RECOVERABLE` | Issues require manual review |
| `TERMINAL_FAILURE` | Recovery failed after max retries |

### E5.2 - Recovery Plan Builder

Creates structured repair plans from release readiness failures.

**Key responsibilities:**
- Map findings to repair actions
- Determine repair action types
- Generate repair prompts for LLM-based repair
- Set priorities based on severity

**Repair Action Types:**
| Type | Auto-Repairable | Category |
|------|-----------------|----------|
| `FIX_SYNTAX` | Yes | SYNTAX |
| `FIX_STRUCTURE` | Yes | STRUCTURE |
| `FIX_CONFIGURATION` | Yes | CONFIGURATION |
| `FIX_DEPENDENCY` | Yes | DEPENDENCY |
| `REMOVE_PLACEHOLDER` | Yes | PLACEHOLDER |
| `ADD_FILE` | Yes | FILESYSTEM |
| `FIX_CONTENT` | Yes | CONTENT |
| `MANUAL_REVIEW` | No | SECURITY, OTHER |
| `REGENERATE` | No | CONTRACT, QUALITY |

### E5.3 - Recovery Engine

Executes recovery with bounded retries.

**Key responsibilities:**
- Execute repair actions
- Enforce workspace boundaries
- Preserve evidence
- Respect retry limits

**Safety Rules:**
1. **Workspace Boundary**: Repairs limited to workspace files
2. **Engine Root Protection**: Cannot modify runtime/ or cli/ files
3. **No Direct Provider Calls**: Must use InvocationEngine
4. **Bounded Retries**: Maximum recovery attempts enforced
5. **Evidence Preservation**: All attempts tracked

---

## 3. Contracts

### Input Contract: `ReleaseReadinessResult`

From E4.3:
```python
class ReleaseReadinessResult(BaseModel):
    readiness_id: str  # "ready-xxxxxx"
    gate_id: str  # Associated QualityGateResult ID
    progression_status: ProgressionStatus
    readiness_level: ReleaseReadinessLevel
    can_release: bool
    blocker_summary: BlockerSummary
    total_findings: int
    # ...
```

### Output Contract: `RecoveryResult`

```python
class RecoveryResult(BaseModel):
    recovery_id: str  # "rcvy-xxxxxx"
    plan_id: str  # Associated RecoveryPlan ID
    readiness_id: str  # Associated ReleaseReadinessResult ID
    success: bool
    can_proceed: bool
    status: RecoveryEligibility
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    resolved_findings: Tuple[str, ...]
    remaining_findings: Tuple[str, ...]
    modified_files: Tuple[str, ...]
    attempts: Tuple[RecoveryAttempt, ...]
    evidence: Dict[str, Any]
    recovery_hash: str  # SHA-256 hash
```

### Intermediate Contract: `RecoveryPlan`

```python
class RecoveryPlan(BaseModel):
    plan_id: str  # "rpln-xxxxxx"
    readiness_id: str
    gate_id: str
    eligibility: RecoveryEligibility
    actions: Tuple[RepairAction, ...]
    total_actions: int
    repairable_actions: int
    manual_actions: int
    max_recovery_attempts: int
    plan_hash: str  # SHA-256 hash
```

---

## 4. Frozen Architecture Guards

E5 implements the following architectural constraints:

```python
FROZEN_ARCHITECTURE_GUARDS = {
    "no_invocation_engine_creation": "E5 must not create a new InvocationEngine instance",
    "no_direct_provider_calls": "E5 must not directly call providers",
    "no_umal_bypass": "E5 must not bypass UMAL",
    "no_frozen_contract_modification": "E5 must not modify frozen E1 contracts",
    "no_unlimited_retries": "E5 must enforce retry limits",
    "no_false_success": "E5 must not mark failed artifacts as successful",
    "no_engine_root_write": "E5 must not write to engine root files",
    "no_bypass_e4_review": "E5 must route repairs through E4.1 review",
}
```

---

## 5. Finding Classification Mapping

Each finding category maps to a repair action type:

| Finding Category | Repair Action Type | Auto-Repairable |
|-----------------|-------------------|-----------------|
| SYNTAX | FIX_SYNTAX | Yes |
| STRUCTURE | FIX_STRUCTURE | Yes |
| CONFIGURATION | FIX_CONFIGURATION | Yes |
| DEPENDENCY | FIX_DEPENDENCY | Yes |
| PLACEHOLDER | REMOVE_PLACEHOLDER | Yes |
| FILESYSTEM | ADD_FILE | Yes |
| CONTENT | FIX_CONTENT | Yes |
| SECURITY | MANUAL_REVIEW | No |
| CONTRACT | MANUAL_REVIEW | No |
| QUALITY | MANUAL_REVIEW | No |
| OTHER | MANUAL_REVIEW | No |

---

## 6. Retry and Termination Semantics

### Retry Limits
- **Default max attempts**: 3 per action
- **Plan max attempts**: Configurable, default 3
- **Automatic termination**: When retry limit reached

### Termination Conditions
1. Max recovery attempts exceeded
2. All repairable actions completed
3. Manual review required
4. Workspace boundary violation

### No Infinite Loops
- Bounded retry counter
- Progress tracking via `RecoveryAttempt`
- Terminal failure state when exhausted

---

## 7. Evidence Preservation

Every recovery operation produces evidence:

```python
RecoveryResult.evidence = {
    "plan_id": str,
    "total_actions": int,
    "recovery_eligibility": str,
}

RecoveryAttempt evidence:
- before_state: State before repair
- after_state: State after repair
- duration_ms: Attempt duration
- result_message: Outcome description
```

---

## 8. Usage Example

```python
from runtime.contracts.e5_engine import RecoveryEngine

# Initialize with workspace root
engine = RecoveryEngine("/path/to/workspace")

# Attempt recovery
plan, result = engine.recover(
    readiness_result,  # From E4.3
    gate_result        # From E4.2
)

# Check outcome
if result.can_proceed:
    print("Recovery successful, project can proceed")
else:
    print(f"Recovery failed: {result.status}")
    print(f"Remaining findings: {result.remaining_findings}")
```

---

## 9. Files Created

| File | Description |
|------|-------------|
| `runtime/contracts/e5_models.py` | E5 data models and contracts |
| `runtime/contracts/e5_engine.py` | Recovery engines (Assessment, Plan, Execution) |
| `tests/runtime/test_e5_self_healing.py` | E5 test suite (29 tests) |
| `docs/E5_SELF_HEALING.md` | This documentation |

---

## 10. Test Coverage

E5 test suite covers:
- Recovery assessment (eligibility determination)
- Recovery plan building
- Finding classification mapping
- Priority determination
- Recovery engine execution
- Evidence preservation
- Frozen architecture compliance
- Determinism verification
- End-to-end pipelines (success and failure)
- Retry limits and termination

---

## 11. Integration Points

E5 integrates with:
- **E4.3** (`ReleaseReadinessResult`) - Input contract
- **E4.2** (`QualityGateResult`) - Finding details
- **E4.1** (`ReviewReport`) - Re-review after repair
- **E3** - Original artifact execution context

E5 does NOT integrate with:
- **P5.E3** - Separate autonomous engineering pipeline
- **E1.1-E1.7** - Frozen runtime contracts
