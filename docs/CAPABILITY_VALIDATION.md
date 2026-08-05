# Capability Resolution Validation Specification (`docs/CAPABILITY_VALIDATION.md`)

## Executive Summary

This document specifies the validation criteria, extraction logic, and auditing rules for **Capability Resolution** in OniRoute (ACR-005 Phase S2).

Capability Resolution is implemented by `CapabilityResolver` and `CapabilityValidator` in `runtime.organization`.

---

## 1. Capability Extraction Pipeline

```text
ExecutionRequest
  ├── Mission Primary Goal -> Search Terms (CRITICAL priority)
  ├── Functional Requirements -> Search Terms (HIGH priority)
  ├── Non-Functional Requirements -> Search Terms (MEDIUM priority)
  └── Operational Constraints -> CapabilityConstraint Records
```

The `CapabilityResolver` parses these requirements and searches repository registries (Agent, Skill, Knowledge, Package, Workflow, Mappings) to identify matching domain capabilities.

---

## 2. Domain Categorization

Capability Resolution supports 14 canonical domains + custom fallbacks:

1. `architecture`: Systems design, module decomposition
2. `backend`: API endpoints, server logic, services
3. `frontend`: Presentation UI, client components, state
4. `database`: Schema design, migrations, queries
5. `security`: Code auditing, authorization rules, compliance
6. `testing`: Unit and integration test suites
7. `qa`: Quality assurance verification, edge cases
8. `devops`: CI/CD pipelines, containerization
9. `infrastructure`: Cloud resources, IaC templates
10. `documentation`: API specs, user guides, changelogs
11. `reviewer`: Static analysis, code quality verification
12. `research`: Benchmarks, tech evaluations
13. `ai`: Prompt engineering, agent tooling, RAG
14. `mobile`: Native & cross-platform mobile apps
15. `custom`: User-defined specialist domains

---

## 3. Validation Audit Rules

The `CapabilityValidator` checks:

1. **Coverage Check**: Asserts $\ge 80\%$ (or $100\%$) of requirements map to capabilities.
2. **Duplicate Check**: Asserts zero duplicate capability IDs.
3. **Conflict Check**: Identifies conflicting operational constraints (e.g. `local_only` vs remote provider requirements).
4. **Dependency Check**: Verifies all referenced capability dependencies exist.
5. **Evidence Completeness**: Confirms every capability has a `CapabilityEvidence` record.
