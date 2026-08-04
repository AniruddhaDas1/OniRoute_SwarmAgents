from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
import networkx as nx

from .models import RepositoryRegistry, ValidationIssue, ValidationReport


class ValidationEngine:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    def _issue(self, report: ValidationReport, severity: str, code: str, message: str, path: Path | None = None) -> None:
        report.issues.append(ValidationIssue(severity=severity, code=code, message=message, path=path))

    def _schema_required(self, path: Path) -> list[str]:
        if not path.exists():
            return []
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return list(data.get("required", []))

    def validate(self, registry: RepositoryRegistry) -> ValidationReport:
        report = ValidationReport()
        for key, paths in registry.duplicates.items():
            self._issue(report, "error", "duplicate_id", f"Duplicate {key}: {', '.join(map(str, paths))}")
        required = self._schema_required(self.root / "workflows/specification/WORKFLOW_SCHEMA.yaml")
        for record in registry.workflows.values():
            missing = [key for key in required if key not in record.data]
            if missing:
                self._issue(report, "error", "missing_metadata", f"Missing Workflow fields: {', '.join(missing)}", record.path)
        index = registry.registry_records.get("WORKFLOW_INDEX")
        if index:
            refs = index.data.get("workflows", [])
            for item in refs:
                workflow_id = item.get("workflow_id") if isinstance(item, dict) else None
                if workflow_id not in registry.workflows:
                    self._issue(report, "error", "broken_reference", f"Registry references missing Workflow: {workflow_id}", index.path)
        graph = nx.DiGraph()
        for record in registry.workflows.values():
            graph.add_node(record.id)
            for dependency in record.data.get("dependencies", []):
                if isinstance(dependency, dict) and dependency.get("kind") == "Workflow":
                    target = dependency.get("id")
                    graph.add_edge(record.id, target)
                    if target not in registry.workflows:
                        self._issue(report, "error", "broken_reference", f"Missing Workflow dependency: {target}", record.path)
        try:
            cycle = nx.find_cycle(graph)
            self._issue(report, "error", "circular_relationship", f"Workflow dependency cycle: {cycle}")
        except nx.NetworkXNoCycle:
            pass
        return report
