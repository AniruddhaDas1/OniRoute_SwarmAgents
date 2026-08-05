# Engineering Collaboration Architecture Blueprint (ACR-007 Phase C1)

**Subsystem:** `runtime/collaboration/`  
**Phase:** C1 — Architecture Only  
**Status:** Specified & Validated  

---

## 1. Executive Summary

This document specifies the complete **Engineering Collaboration Architecture** for OniRoute SwarmAgents.

The Collaboration subsystem enables multi-agent cooperation, typed message passing, zero-duplication artifact handoffs, approval workflows, peer review coordination, and unified timeline logging across live `AgentSession` instances.

It is designed to consume the **frozen Agent Runtime** without introducing execution logic, AI calls, or runtime FSM modifications.

---

## 2. Full Collaboration Pipeline Architecture

$$\text{Agent Runtime} \longrightarrow \text{Collaboration Coordinator} \longrightarrow \text{Message Bus} \longrightarrow \text{Handoff Manager} \longrightarrow \text{Shared Artifact Manager} \longrightarrow \text{Approval Coordinator} \longrightarrow \text{Review Coordinator} \longrightarrow \text{Execution Timeline}$$

---

## 3. Read-Only Engine Integration

The Collaboration layer integrates with the existing OniRoute SwarmAgents engine through read-only consumption of established interfaces:

| Component | Integration Method | Constraint |
|---|---|---|
| **Agent Runtime** | Reads `AgentSession` IDs, roles, and states | NO mutation of `AgentSession` or `RuntimeState` |
| **Artifact Router** | Reads `ArtifactRecord` IDs and metadata | NO duplication of files or workspace assets |
| **Reports** | Reads `RuntimeReport` and `RecoveryReport` | NO modification of report schemas |
| **Workspace Storage** | Writes `CollaborationReport` and timeline logs to workspace storage | NO engine source mutation |
| **Traces & History** | Appends `TimelineEvent` records to workspace execution history | NO modification of existing trace formats |

---

## 4. Execution Timeline Log (`Timeline`)

The `Timeline` object consolidates all collaboration activity into a single, append-only chronological log:

- `MESSAGE` — Inter-agent message published to bus
- `HANDOFF` — Deliverable handoff initiated, accepted, or rejected
- `REVIEW` — Peer review requested or completed
- `APPROVAL` — Governance or peer approval request/decision
- `ARTIFACT_SHARED` — Shared artifact reference registered
- `STATE_CHANGED` — Session state or collaboration status updated

---

## 5. Phase C2 Roadmap

Phase C1 certifies the architecture, contracts, and immutable data models.

Phase C2 will implement the deterministic **Message Bus** and **Collaboration Sessions** components:
- Concrete `MessageBus` implementation with thread routing
- Concrete `HandoffManager` implementation with status validation
- Concrete `CollaborationCoordinator` producing `CollaborationReport`
- Zero modification to frozen Agent Runtime, Mission, Organization, or Workspace layers.
