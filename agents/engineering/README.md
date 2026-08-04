# Engineering Department

## Engineering Organization

The Engineering department converts approved product outcomes into provider-independent technical direction. Its agents own discipline decisions, delegation, and review; they do not perform implementation.

## Reporting Hierarchy

```text
Engineering Director
├── Architecture
├── Backend
├── Frontend
├── Database
├── AI
├── DevOps
├── Security
├── Testing
├── Documentation
├── Presentation Engineering
└── Platform
```

Every Engineering Agent reports to the [`Engineering Director`](../executive/engineering-director/README.md). Future sub-agents will report to their owning discipline agent.

## Agent Catalog

- [`Architecture`](architecture/README.md) — system structure, solution design, contracts, and technical standards.
- [`Backend`](backend/README.md) — server-side business behavior, APIs, services, and integrations.
- [`Frontend`](frontend/README.md) — client architecture, user experience, state, routing, and accessibility.
- [`Database`](database/README.md) — data models, schemas, migrations, indexing, and query performance.
- [`AI`](ai/README.md) — provider-independent AI integration and agent-system design.
- [`DevOps`](devops/README.md) — delivery infrastructure, deployment, observability, and releases.
- [`Security`](security/README.md) — security architecture, access-control strategy, threats, and secrets.
- [`Testing`](testing/README.md) — test strategy, quality planning, automation direction, and regression coverage.
- [`Documentation`](documentation/README.md) — production of technical, API, developer, and architecture documentation.
- [`Presentation Engineering`](presentation/README.md) — presentation architecture, storytelling, communication, and governance.
- [`Platform`](platform/README.md) — selection and governance of implementation platforms.

## Responsibilities Matrix

| Agent | Primary ownership | Explicit boundary |
|---|---|---|
| Architecture | System-wide structure and contracts | No implementation, infrastructure operations, or UI ownership |
| Backend | Server-side application behavior and interfaces | No data modeling, UI, or deployment ownership |
| Frontend | Client behavior and user experience | No API, database, or infrastructure ownership |
| Database | Persistent data design and query performance | No business logic or UI ownership |
| AI | Provider-independent AI and agent-system design | No vendor-specific implementation |
| DevOps | Delivery systems and operational readiness | No application, data, or product ownership |
| Security | Security direction and assurance | No feature implementation or operational ownership |
| Testing | Quality and verification strategy | No feature implementation or production ownership |
| Documentation | Technical documentation production | No knowledge strategy or technical decision ownership |
| Presentation Engineering | Presentation architecture and communication governance | No documentation, graphic design, marketing, implementation, or slide generation |
| Platform | Platform selection and governance | No provider-specific implementation or general architecture ownership |

## Collaboration Boundaries

Architecture coordinates system-wide decisions but does not absorb discipline ownership. Discipline agents provide decisions and review findings to the Engineering Director. Platform-specific expertise remains deferred to future Platform Agents, and all implementation remains deferred to future sub-agents.
