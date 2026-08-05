# Engineering Collaboration User Guide (ACR-007)

A practical guide for developers and operators managing inter-agent collaboration, conversations, threads, shared artifacts, handoffs, reviews, and approvals using the `oniroute` CLI.

---

## 1. CLI Command Overview

The `oniroute` CLI provides 7 dedicated collaboration management commands:

| Command | Purpose |
|---|---|
| `oniroute collaborate` | Initialize a collaboration session with conversation, thread, and message bus |
| `oniroute conversation` | Inspect active conversations and participant threads |
| `oniroute thread` | View message threads and message history |
| `oniroute artifact` | Inspect shared artifact references, ownership, versioning, and lineage |
| `oniroute handoff` | View and track inter-session deliverable and task handoffs |
| `oniroute review` | Inspect inter-agent peer reviews or submit recovery review decisions |
| `oniroute approval` | Inspect governance approval requests, policy decisions, and pending approvals |

---

## 2. Usage Examples

### 1. Collaborate Command
```bash
# Initialize a collaboration session
oniroute collaborate "Design REST API for Payment Gateway"

# Machine-readable JSON output
oniroute collaborate "Design REST API for Payment Gateway" --json
```

### 2. Conversation & Thread Management
```bash
# View active conversations
oniroute conversation

# Inspect specific conversation
oniroute conversation --id conv-a1b2c3d4 --json

# View thread history
oniroute thread
oniroute thread th-api-001 --json
```

### 3. Shared Artifact References
```bash
# View shared artifact references (zero content duplication)
oniroute artifact

# Inspect specific reference by ID
oniroute artifact --id ref-spec-001 --json
```

### 4. Deliverable & Task Handoffs
```bash
# View all inter-session handoffs
oniroute handoff

# Filter handoffs by session ID
oniroute handoff --session sess-arch-001 --json
```

### 5. Peer Reviews & Governance Approvals
```bash
# View inter-agent peer reviews
oniroute review

# View governance approvals under Security policy
oniroute approval --policy security

# Output raw JSON
oniroute approval --json
```
