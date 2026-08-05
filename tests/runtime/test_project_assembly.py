"""Tests for Complete Project Assembly Pipeline & Certification (Phase P4.G5)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.assembly import (
    ProjectAssemblyCertificationEngine,
    ProjectAssemblyCertificationReport,
)


def test_project_assembly_certification_full(tmp_path: Path):
    """Verify complete end-to-end Project Assembly certification pipeline."""
    engine = ProjectAssemblyCertificationEngine()
    cert_report = engine.certify_assembly(tmp_path)

    assert isinstance(cert_report, ProjectAssemblyCertificationReport)
    assert cert_report.certified is True
    assert cert_report.determinism_verified is True
    assert cert_report.serialization_verified is True
    assert cert_report.pipeline_integrity_verified is True
    assert cert_report.zero_llm_invocations is True
    assert cert_report.zero_code_generation is True
    assert cert_report.total_assembly_latency_ms < 500.0
    assert cert_report.certification_hash != ""


def test_project_assembly_cli(tmp_path: Path):
    """Verify oniroute certify-assembly CLI command execution."""
    runner = CliRunner()

    result = runner.invoke(app, ["certify-assembly", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project Assembly Certified & Frozen" in result.output

    result_json = runner.invoke(app, ["certify-assembly", "--workspace", str(tmp_path), "--json"])
    assert result_json.exit_code == 0
    json_data = json.loads(result_json.output)
    assert "certification_id" in json_data
    assert json_data["certified"] is True
