# Organization Builder Developer Guide (`docs/ORGANIZATION_DEVELOPER_GUIDE.md`)

## Executive Summary

This guide provides technical reference instructions for developers consuming or extending the **Engineering Organization Builder** package (`runtime.organization`).

---

## 1. Programmatic Python SDK Usage

```python
from pathlib import Path
from runtime.mission import MissionIntake, MissionResolver, MissionOrchestrator
from runtime.organization import (
    CapabilityResolver,
    OrganizationAssembler,
    SwarmGraphBuilder,
    ExecutionBlueprintAssembler,
    ExecutionBlueprint,
)

# Step 1: Prepare ExecutionRequest
intake = MissionIntake()
mission_req = intake.process_intake("Create CRM with FastAPI backend")
resolved_mission = MissionResolver().resolve_mission(mission_req)
exec_request = MissionOrchestrator().orchestrate_mission(resolved_mission)

# Step 2: Resolve Capabilities
cap_resolver = CapabilityResolver()
cap_report = cap_resolver.resolve_capabilities(exec_request)

# Step 3: Assemble Organization
org_assembler = OrganizationAssembler()
organization = org_assembler.assemble_organization(cap_report)

# Step 4: Build Swarm Graph
sg_builder = SwarmGraphBuilder()
swarm_graph = sg_builder.build_swarm_graph(organization)

# Step 5: Assemble & Seal Execution Blueprint
bp_assembler = ExecutionBlueprintAssembler()
blueprint: ExecutionBlueprint = bp_assembler.create_blueprint(
    exec_request, organization, cap_report, swarm_graph
)

print(f"Sealed Blueprint ID: {blueprint.blueprint_id}")
print(f"Readiness Status: {blueprint.readiness.is_ready}")
```

---

## 2. Interface Contracts

Custom implementations or extensions must implement the frozen contracts in `runtime.organization.contracts`:

- `CapabilityAnalyzerContract`: Method `analyze_capabilities(request: ExecutionRequest) -> CapabilityReport`
- `OrganizationBuilderContract`: Method `build_organization(report: CapabilityReport) -> Organization`
- `OrganizationValidatorContract`: Method `validate_organization(org: Organization) -> OrganizationReport`
- `SwarmGraphBuilderContract`: Method `build_swarm_graph(org: Organization) -> SwarmGraph`
- `ExecutionBlueprintBuilderContract`: Method `create_blueprint(...) -> ExecutionBlueprint`

---

## 3. Mandatory Safety Constraints

- **Read-Only Operation**: Developers must not add registry mutations or filesystem writes inside resolver engines.
- **Zero Runtime Logic**: Never introduce execution loops, thread pool dispatchers, or LLM API calls inside the Organization Builder.
