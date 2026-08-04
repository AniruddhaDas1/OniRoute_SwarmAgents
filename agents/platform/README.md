# Platform Department

## Purpose of Platform Layer

The Platform layer provides technology-specific expertise to the provider-independent Engineering organization. Platform Agents evaluate capabilities, constraints, risks, trade-offs, integrations, migrations, best practices, and portability without implementing code or operating infrastructure.

## Reporting Structure

```text
Engineering Director
└── Engineering Platform Agent
    ├── Supabase
    ├── Appwrite
    ├── Firebase
    ├── PostgreSQL
    ├── Redis
    ├── Docker
    ├── Kubernetes
    ├── AWS
    ├── Azure
    ├── Google Cloud
    ├── Cloudflare
    └── Vercel
```

All Platform Agents report to the [`Engineering Platform Agent`](../engineering/platform/README.md). They advise selection and governance but do not make final platform decisions.

## Platform Catalog

- [`Supabase`](supabase/README.md) — integrated relational backend services.
- [`Appwrite`](appwrite/README.md) — integrated application backend services with deployment flexibility.
- [`Firebase`](firebase/README.md) — managed mobile and web application services.
- [`PostgreSQL`](postgresql/README.md) — relational data and transactional database technology.
- [`Redis`](redis/README.md) — low-latency caching, transient data, and coordination technology.
- [`Docker`](docker/README.md) — container packaging and portable runtime artifacts.
- [`Kubernetes`](kubernetes/README.md) — container orchestration and distributed workload management.
- [`AWS`](aws/README.md) — broad global cloud platform capabilities.
- [`Azure`](azure/README.md) — enterprise, hybrid, and managed cloud capabilities.
- [`Google Cloud`](google-cloud/README.md) — cloud application, data, analytics, and machine-learning capabilities.
- [`Cloudflare`](cloudflare/README.md) — edge delivery, security, networking, and compute capabilities.
- [`Vercel`](vercel/README.md) — managed frontend and web application delivery capabilities.

## Interaction with Engineering Agents

- The Engineering Platform Agent provides evaluation criteria and requests technology-specific evidence.
- Platform Agents return capability analysis, constraints, risks, trade-offs, portability guidance, and recommendations.
- Architecture retains system-design ownership; Database, AI, DevOps, Security, Backend, and Frontend retain their discipline decisions.
- The Engineering Platform Agent integrates comparative evidence and owns platform selection and governance recommendations.

## Interaction with Future Platform Sub-Agents

Future Platform Sub-Agents will report to their technology's Platform Agent and may perform bounded implementation tasks. Platform Agents will retain technology direction, review, and advisory accountability without performing implementation themselves.

## Boundaries

Platform Agents do not own code generation, implementation, deployment, infrastructure execution, business logic, product decisions, skills, workflows, adapters, or executable runtime behavior.
