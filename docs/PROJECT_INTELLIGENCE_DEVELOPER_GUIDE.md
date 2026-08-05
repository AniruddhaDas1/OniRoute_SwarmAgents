# Project Intelligence Developer Guide

## 1. Introduction
This guide explains how developers and programmatic integrations interact with the **OniRoute Project Intelligence Subsystem**.

---

## 2. Python SDK Usage

### 2.1 Full Pipeline Execution
```python
from pathlib import Path
from runtime.intent import IntentAnalyzer
from runtime.workspace import (
    WorkspaceIntelligence,
    RepositoryIntelligence,
    EngineeringPlanGenerator,
)

# 1. Intent Analysis
raw_request = "Build a luxury real estate website using Next.js and Supabase"
intent_analyzer = IntentAnalyzer()
intent_report = intent_analyzer.analyze(raw_request)

# 2. Workspace Intelligence
ws_intelligence = WorkspaceIntelligence()
workspace_context = ws_intelligence.analyze_workspace(cwd=Path.cwd())

# 3. Repository Intelligence
repo_intelligence = RepositoryIntelligence()
repository_context = repo_intelligence.analyze_repository(workspace_context)

# 4. Engineering Execution Plan
plan_generator = EngineeringPlanGenerator()
execution_plan = plan_generator.generate_plan(
    intent_report, workspace_context, repository_context
)

print(f"Plan ID: {execution_plan.plan_id}")
print(f"Strategy: {execution_plan.repository_strategy}")
print(f"Disciplines: {execution_plan.required_disciplines}")
print(f"Deliverables: {execution_plan.required_deliverables}")
```

---

## 3. CLI Command Reference

### 3.1 Intent Analysis Diagnostic
```bash
oniroute intent "Build a CRM web application using FastAPI and React"
oniroute intent "Build a CRM web application using FastAPI and React" --json
```

### 3.2 Workspace Context Diagnostic
```bash
oniroute workspace-context
oniroute workspace-context --json
```

### 3.3 Repository Intelligence Diagnostic
```bash
oniroute repository
oniroute repository --json
```

### 3.4 Engineering Execution Plan Diagnostic
```bash
oniroute plan "Build CRM"
oniroute plan "Build CRM" --json
```

---

## 4. Model Serialization & Export
All Project Intelligence context models implement standard Pydantic JSON export:

```python
json_str = execution_plan.model_dump_json(indent=2)
# Deserialization
from runtime.workspace import EngineeringExecutionPlan
reconstructed_plan = EngineeringExecutionPlan.model_validate_json(json_str)
```
