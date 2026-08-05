# Phase P3.A4 — Consensus Protocol Specification

## 1. Subsystem Overview
The [`SwarmConsensusEngine`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/consensus.py#L30) drives consensus protocols across execution waves, review gates, and human approval gates.

```
Wave Execution ──► Review Gate / Approval Gate ──► SwarmConsensusEngine ──► SwarmConsensusRecord
```

---

## 2. Supported Consensus Types

1. **Review Approval (`REVIEW_APPROVAL`)**: Single or primary agent review of wave deliverables (`APPROVED`, `CHANGES_REQUESTED`).
2. **Human Approval (`HUMAN_APPROVAL`)**: Human checkpoint evaluation (`APPROVED`, `REJECTED`, `AUTOMATIC`).
3. **Multi-Agent Agreement (`MULTI_AGENT_AGREEMENT`)**: Collaborative vote across participant agent profiles (`UNANIMOUS_APPROVAL`, `MAJORITY_APPROVAL`).
4. **Conflict Escalation (`ESCALATED_TO_HUMAN`)**: Automated escalation when agents disagree or threshold rules trigger.
5. **Lead Role Tie Resolution**: Lead role vote applied as tie-breaker when votes are evenly split (`tie_breaker_applied = true`).

---

## 3. SwarmConsensusRecord Schema

```json
{
  "consensus_id": "csn-w2-7206326b",
  "wave_number": 2,
  "gate_name": "Wave 2 Execution & Review Gate",
  "consensus_type": "MULTI_AGENT_AGREEMENT",
  "decision": "APPROVED",
  "votes": {
    "ap-ai-22007d": "APPROVED",
    "ap-backend-22007d": "APPROVED",
    "ap-frontend-22007d": "APPROVED"
  },
  "tie_breaker_applied": false,
  "consensus_hash": "6e0980198c02a3fd4f27db70a65c0242dbb663cd1b27120744b746cdc9440176",
  "timestamp": "2026-08-05T21:30:00+00:00"
}
```
