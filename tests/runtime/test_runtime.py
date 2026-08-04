from pathlib import Path

import yaml

from runtime.loader import RepositoryLoader
from runtime.registry import RegistryBuilder
from runtime.models import MetadataRecord
from runtime.resolver import Resolver
from runtime.validator import ValidationEngine


ROOT = Path(__file__).parents[2]


def test_repository_loading_and_registry_creation():
    registry = RepositoryLoader(ROOT).load()
    assert registry.agents
    assert registry.skills
    assert len(registry.workflows) == 20
    assert registry.registry_records


def test_yaml_validation_and_registry_references():
    registry = RepositoryLoader(ROOT).load()
    report = ValidationEngine(ROOT).validate(registry)
    assert report.valid, report.errors


def test_duplicate_detection(tmp_path):
    builder = RegistryBuilder(tmp_path)
    record = MetadataRecord(id="same", kind="skill", path=tmp_path / "one.yaml", data={})
    builder.register(record)
    builder.register(record.model_copy(update={"path": tmp_path / "two.yaml"}))
    assert "skill:same" in builder.registry.duplicates


def test_reference_validation(tmp_path):
    (tmp_path / "workflows/official/example").mkdir(parents=True)
    (tmp_path / "workflows/registry").mkdir(parents=True)
    (tmp_path / "workflows/specification").mkdir(parents=True)
    (tmp_path / "workflows/official/example/workflow.yaml").write_text("workflow_id: example\n", encoding="utf-8")
    (tmp_path / "workflows/specification/WORKFLOW_SCHEMA.yaml").write_text("required: [workflow_id]\n", encoding="utf-8")
    index = {"workflows": [{"workflow_id": "missing"}]}
    (tmp_path / "workflows/registry/WORKFLOW_INDEX.yaml").write_text(yaml.safe_dump(index), encoding="utf-8")
    report = ValidationEngine(tmp_path).validate(RepositoryLoader(tmp_path).load())
    assert any(issue.code == "broken_reference" for issue in report.errors)


def test_read_only_resolver():
    resolver = Resolver(RepositoryLoader(ROOT).load())
    assert resolver.find_workflow("rest-api-design") is not None
    assert resolver.search_by_category("Backend")
