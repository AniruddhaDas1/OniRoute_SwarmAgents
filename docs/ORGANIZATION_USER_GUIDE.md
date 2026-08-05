# Organization Builder User Guide (`docs/ORGANIZATION_USER_GUIDE.md`)

## Executive Summary

This guide provides end-user instructions for inspecting capability requirements, engineering organization structures, and sealed execution blueprints via the OniRoute CLI.

---

## 1. CLI Commands Reference

### 1. Capability Resolution (`oniroute capability`)
Resolves required engineering capabilities for a mission command without creating an organization or executing tasks.

```bash
# Display formatted Rich table of resolved capabilities
oniroute capability "Create a SaaS CRM with REST API"

# Display raw JSON CapabilityReport
oniroute capability --json "Build REST API"

# Explicit workspace override
oniroute capability --workspace /path/to/project "Refactor auth system"
```

### 2. Organization Assembly (`oniroute organization`)
Assembles and displays the engineering swarm organization (roles, member slots, departments, reporting lines).

```bash
# Display Rich table of assembled swarm members and departments
oniroute organization "Create portfolio website"

# Output raw JSON Organization schema
oniroute organization --json "Build microservice backend"
```

### 3. Execution Blueprint Assembly (`oniroute blueprint`)
Assembles and displays the sealed execution blueprint, combining mission, capabilities, organization, swarm graph, and readiness verification.

```bash
# Display Rich table of sealed blueprint attributes and readiness checks
oniroute blueprint "Create CRM"

# Output raw JSON ExecutionBlueprint
oniroute blueprint --json "Build REST API"
```

---

## 2. Output Formatting Options

All commands support both human-readable **Rich table** displays and machine-readable `--json` flag output. The `--json` flag is ideal for pipeline integrations and script automation.
