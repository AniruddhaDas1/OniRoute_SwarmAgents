# Project Intelligence Freeze Declaration (Phase P1.I5)

## 1. Freeze Notice
As of **Phase P1.I5**, the **Project Intelligence Subsystem** of OniRoute v1.2 is officially **FROZEN**.

No further functional changes, architectural modifications, model schema alterations, or CLI command additions are permitted within the Project Intelligence subsystem for the remainder of v1.2 development, except for critical bug fixes.

---

## 2. Frozen Scope & Components

### 2.1 Frozen Models & Contracts
- `IntentReport` (`runtime/intent/models.py`)
- `WorkspaceContext` (`runtime/workspace/intelligence.py`)
- `RepositoryContext` (`runtime/workspace/repository.py`)
- `EngineeringExecutionPlan` (`runtime/workspace/plan.py`)
- `RepositoryStrategy` (`runtime/workspace/plan.py`)
- `WorkspaceState` (`runtime/workspace/intelligence.py`)

### 2.2 Frozen Engines & Analyzers
- `IntentAnalyzer` (`runtime/intent/analyzer.py`)
- `WorkspaceIntelligence` (`runtime/workspace/intelligence.py`)
- `RepositoryIntelligence` (`runtime/workspace/repository.py`)
- `EngineeringPlanGenerator` (`runtime/workspace/plan.py`)

### 2.3 Frozen CLI Diagnostic Subcommands
- `oniroute intent "<request>"`
- `oniroute workspace-context`
- `oniroute repository`
- `oniroute plan "<request>"`

---

## 3. Governance Policy Post-Freeze
1. **Backward Compatibility**: Any future change must maintain 100% backward compatibility with serialized JSON schemas of all four frozen models.
2. **Deterministic Guarantee**: No non-deterministic logic or external network calls may be introduced into the Project Intelligence pipeline.
3. **No AST / Code Execution**: The subsystem must remain strictly free of AST parsing or business logic code execution.
4. **Subsystem Handoff**: Downstream Phase P2 (**Skill Intelligence**) must consume `EngineeringExecutionPlan` as its sole planning contract without inspecting natural language or modifying Project Intelligence engines.
