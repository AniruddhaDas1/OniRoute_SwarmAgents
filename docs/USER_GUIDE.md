# OniRoute Swarm AI Engine User Guide (Phase P6.D1)

## 1. Introduction

OniRoute Engine v1.2 is an autonomous multi-agent swarm platform. It allows engineers and developers to build, fix, refactor, and migrate software applications using plain natural language prompts.

---

## 2. Getting Started

### Installation & Prerequisites
Ensure Python 3.10+ is installed in your environment.
```bash
pip install -e .
```

---

## 3. Usage Examples

### Build a Web Application
```bash
oniroute build real-estate website
```

### Create a SaaS CRM
```bash
oniroute create SaaS CRM
```

### Programmatic Python Usage
```python
from runtime.router import NaturalLanguageRouter

router = NaturalLanguageRouter()
result = router.route_and_execute("build a real estate website")

print(f"Mission ID: {result.mission_id}")
print(f"Files Created: {result.total_files_created}")
print(f"Production Ready: {result.production_ready}")
```
