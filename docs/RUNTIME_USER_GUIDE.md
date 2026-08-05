# Agent Runtime User Guide (ACR-006 Phase R5)

This guide explains how operators and users interact with the **OniRoute Agent Runtime** via CLI commands and basic configuration.

---

## 1. CLI Command Quick Reference

The `oniroute` CLI provides six primary commands for inspecting and driving agent sessions and runtime recovery:

```
oniroute session      Initialize and list agent sessions from an ExecutionBlueprint
oniroute execute      Execute a mission end-to-end (Blueprint → Sessions → Invocations → Report)
oniroute review       Submit human review decisions (APPROVE / REJECT / REQUEST-CHANGES)
oniroute retry        Inspect retry eligibility, backoff delay, and retry policies
oniroute resume       Resume paused sessions from WAITING to RUNNING
oniroute recovery     Generate and view structured RecoveryReports
```

---

## 2. Session Initialization & Inspection

Initialize sessions for a workspace without executing them:

```bash
# Formatted table output
oniroute session "Implement authentication service"

# Machine-readable JSON output
oniroute session "Implement authentication service" --json
```

---

## 3. Mission Execution

Execute all READY sessions for a mission end-to-end:

```bash
# Execute mission end-to-end
oniroute execute "Build payment gateway integration"

# Explicit workspace override
oniroute execute --workspace /path/to/project "Build payment gateway"
```

---

## 4. Human Review & Approval

When an agent session produces sensitive artifacts (e.g. security schemas, configuration changes, infrastructure specs), it enters the `REVIEW` state.

Use `oniroute review` to submit a reviewer decision:

```bash
# Approve a session under review
oniroute review sess-backend-001 --approve --actor "security-lead" --notes "Approved for deployment"

# Reject a session under review
oniroute review sess-backend-001 --reject --actor "qa-lead" --notes "Security vulnerability detected"

# Request changes
oniroute review sess-backend-001 --request-changes --actor "reviewer" --notes "Update database migration script"

# Apply custom policy check
oniroute review sess-backend-001 --approve --policy security
```

---

## 5. Retry & Failure Inspection

Inspect retry eligibility and policy for a failed session:

```bash
# Inspect retry status
oniroute retry sess-backend-001

# Inspect with custom retry policy limits
oniroute retry sess-backend-001 --max-retries 5 --base-delay 2.0 --json
```

---

## 6. Resuming Paused Sessions

Resume a session that was paused in the `WAITING` state:

```bash
# Resume most recent pause
oniroute resume sess-backend-001

# Resume specific pause record
oniroute resume sess-backend-001 --pause-id pause-sess-backend-001-a1b2c3
```

---

## 7. Recovery Reporting

Generate a complete `RecoveryReport` capturing all failure classifications, retries, pauses, and reviews for a session:

```bash
# Human-readable table
oniroute recovery sess-backend-001

# JSON report
oniroute recovery sess-backend-001 --json
```
