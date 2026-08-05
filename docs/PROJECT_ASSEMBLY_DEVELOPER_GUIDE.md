# Project Assembly Developer & Integration Guide (Phase P4.G5)

## 1. Programmatic Assembly Execution

Developers can execute the complete end-to-end Project Assembly pipeline programmatically:

```python
from pathlib import Path
from runtime.scaffold import WorkspaceScaffoldEngine
from runtime.blueprint import ProjectBlueprintEngine
from runtime.allocation import ImplementationAllocationEngine
from runtime.contracts import EngineeringContractEngine
from runtime.assembly import ProjectAssemblyCertificationEngine

# 1. Run Certification Audit
cert_engine = ProjectAssemblyCertificationEngine()
cert_report = cert_engine.certify_assembly(Path.cwd())

assert cert_report.certified is True
print(f"Certification ID: {cert_report.certification_id}")
print(f"Assembly Latency: {cert_report.total_assembly_latency_ms:.2f} ms")
```

---

## 2. CLI Reference

```bash
# Run end-to-end Project Assembly certification audit
oniroute certify-assembly

# Output raw JSON certification report
oniroute certify-assembly --json
```

---

## 3. Transition to Phase P5 (Autonomous Engineering)

With Phase P4 complete and frozen, **Phase P5 (Autonomous Engineering)** will begin in Phase P5.E1.
The first autonomous coding agent will consume ONLY `EngineeringContractReport` to generate and modify application source code files in execution waves.
