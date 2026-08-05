# Workspace Architecture Architectural Freeze Certificate (`docs/WORKSPACE_FREEZE.md`)

## Executive Certificate

**Repository**: `OniRoute_SwarmAgents`  
**Framework Version**: `OniRoute v1.0.0`  
**Architecture Record**: `ACR-003 Phase W5`  
**Freeze Date**: August 5, 2026  
**Status**: **FROZEN & CERTIFIED**

---

## 1. Scope of Architectural Freeze

Effective immediately upon completion of ACR-003 Phase W5, the **Workspace Architecture** is formally frozen. The following core modules, contracts, metadata models, and CLI tools are locked:

1. **Workspace API Contracts (`runtime/workspace/contracts.py`)**:
   - `WorkspaceManagerContract`
   - `WorkspaceResolverContract`
   - `ArtifactRouterContract`
   - `EngineResolverContract`
2. **Workspace Canonical Models (`runtime/workspace/models.py`)**:
   - `WorkspaceMetadata`
   - `ProjectMetadata`
   - `ExecutionContext`
   - `ArtifactCategory`, `ArtifactDestination`, `ArtifactRecord`, `ArtifactOwnership`
   - `DiscoveryPriority`, `WorkspaceLifecycle`, `WorkspaceStatus`, `TrustLevel`
3. **Workspace Discovery & Resolution (`runtime/workspace/discovery.py`, `engine.py`, `project.py`)**:
   - 4-level deterministic discovery priority cascade.
   - Read-only Engine Root resolution.
   - Multi-ecosystem project detector.
4. **Workspace Storage & Subdirectory Schema (`runtime/workspace/storage.py`)**:
   - Canonical 16 `.oniroute/` subdirectories layout (`sessions`, `history`, `plans`, `traces`, `artifacts`, `generated`, `temporary`, `reports`, `approvals`, `cache`, `logs`, `memory`, `context`, `knowledge`, `runtime`, `locks`).
   - Lazy directory creation semantics.
   - `workspace.yaml` serialization format.
5. **Engine Safety Guards (`runtime/workspace/engine_safety.py`)**:
   - `assert_within_workspace()`
   - `assert_outside_engine()`
   - `assert_no_engine_write()`
6. **Artifact Router (`runtime/workspace/artifact_router.py`)**:
   - Category-to-subdirectory routing map.
   - Collision resolution policies (lenient timestamping & strict error mode).
7. **Workspace Runtime & Storage Persistence (`runtime/workspace/*_storage.py`)**:
   - `ExecutionHistoryStorage` (`.oniroute/history/`)
   - `TraceStorage` (`.oniroute/traces/`)
   - `SessionStorage` (`.oniroute/sessions/`)
   - `ReportStorage` (`.oniroute/reports/`)
   - `LogStorage` (`.oniroute/logs/`)
8. **Workspace CLI Commands (`cli/main.py`)**:
   - `oniroute workspace`
   - `oniroute doctor`
   - `oniroute history`
   - `oniroute events` (traces)
   - `--workspace` / `-w` global options.

---

## 2. Invariant Rules for Future ACRs

1. **No API Redesign**: No subsequent ACR (including ACR-004 Mission Orchestrator) may modify, break, or redesign the Workspace contracts or metadata models.
2. **Bug Fix Exemption Only**: Future modifications to frozen workspace files are restricted strictly to security patches or non-breaking bug fixes.
3. **Engine Safety Mandate**: Future components (such as Mission Orchestrator, Swarm Agents, and Memory engines) MUST consume `ExecutionContext` and pass all filesystem writes through `WorkspaceStorage` or `ArtifactRouter`. Zero writes inside Engine Root are permitted.

---

## 3. Sign-off & Verification

- **All 132 Tests Passing**: Confirmed (`0` failures, `0` regressions).
- **Engine Safety Boundary**: Confirmed and enforced.
- **Documentation Suite Complete**: Confirmed.
- **Freeze Status**: ACTIVE.
