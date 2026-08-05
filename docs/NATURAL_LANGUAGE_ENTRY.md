# Natural Language Entry Specification (Phase P6.D1)

## 1. Overview

The **Natural Language Entry** mechanism provides a single, unified public entrance to the **OniRoute Swarm AI Engine v1.2**.

Users submit plain natural language requests (e.g., `oniroute build a real estate website`, `oniroute create SaaS CRM`). The [`NaturalLanguageRouter`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/router/router.py#L38) automatically resolves all architectural decisions, skill selections, profile builder deployments, project assembly, autonomous code generation, cross-agent quality review, self-healing repairs, deterministic verification, and release certification.

---

## 2. End-to-End Automated Pipeline

```
Natural Language Request ("oniroute build a real estate website")
                        │
                        ▼
            Intent Analysis (P1)
                        │
                        ▼
      Workspace & Repository Intelligence (P1)
                        │
                        ▼
            Smart Defaults Resolution
                        │
                        ▼
         Mission & Engineering Planning (P1)
                        │
                        ▼
       Skill Intelligence & Profile Building (P2)
                        │
                        ▼
            Swarm Initialization (P3)
                        │
                        ▼
  Project Assembly (Scaffold, Blueprint, Allocation, Contracts, Assembly Cert) (P4)
                        │
                        ▼
  Autonomous Engineering (Worker, Quality Gate, Healing, Verification, Acceptance, Cert) (P5)
                        │
                        ▼
            Finished Certified Project
```

---

## 3. Smart Defaults Resolution

The router automatically resolves 14 smart defaults without user intervention:

| Category | Default Inferred Value |
|---|---|
| **Project Type** | `typescript` / `python` / `go` / `rust` |
| **Technology Stack** | Next.js 14 + React + Tailwind CSS + TypeScript + PostgreSQL |
| **Framework** | Next.js / FastAPI / Gin |
| **Database** | PostgreSQL |
| **Authentication** | JWT / OAuth2 / NextAuth |
| **Deployment Target** | Vercel / Docker Container |
| **Testing Framework** | Vitest + Playwright / pytest |
| **Package Manager** | npm / pip / go mod |
| **Coding Standards** | ESLint + Prettier / PEP8 |
| **LLM Provider** | `oniroute-local-engine` |
| **MCP Tools** | BridgeForce, StitchMCP, Chrome DevTools, Firebase MCP |
| **Review Strategy** | Cross-Agent 5-Profile Quality Review |
| **Healing Strategy** | Automated Self-Healing |
| **Verification Strategy** | Deterministic Build & Coverage Verification |
