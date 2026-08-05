import pytest
from pathlib import Path

from cli.main import REGISTERED_CLI_COMMANDS, main
from runtime.mission import (
    EmptyCommandError,
    MissionIntake,
    MissionNormalizer,
    MissionRequest,
    MissionState,
    WorkspaceUnavailableError,
)


def test_mission_normalizer_simple():
    norm = MissionNormalizer.normalize("Create portfolio website")
    assert norm == "Create portfolio website"
    cmd, inst = MissionNormalizer.extract_structure(norm)
    assert cmd == "Create"
    assert inst == "portfolio website"


def test_mission_normalizer_whitespace_and_unicode():
    raw = "   Build   CRM   \n\t  with   e-commerce   café   "
    norm = MissionNormalizer.normalize(raw)
    assert norm == "Build CRM with e-commerce café"
    cmd, inst = MissionNormalizer.extract_structure(norm)
    assert cmd == "Build"
    assert inst == "CRM with e-commerce café"


def test_mission_intake_simple_request():
    intake = MissionIntake()
    req = intake.process_intake("Create portfolio website")

    assert isinstance(req, MissionRequest)
    assert req.mission_id.startswith("msn-")
    assert req.request_id.startswith("req-")
    assert req.original_command == "Create portfolio website"
    assert req.normalized_command == "Create portfolio website"
    assert req.raw_prompt == "Create portfolio website"
    assert req.mission_state == MissionState.RECEIVED
    assert req.source == "cli"
    assert req.version == "1.0.0"
    assert req.metadata["primary_command"] == "Create"
    assert req.metadata["instruction"] == "portfolio website"


def test_mission_intake_long_command():
    raw = "Build a full stack enterprise SaaS CRM web application with authentication and dashboard"
    intake = MissionIntake()
    req = intake.process_intake(raw)

    assert req.normalized_command == raw
    assert req.metadata["primary_command"] == "Build"


def test_mission_intake_empty_request_raises():
    intake = MissionIntake()
    with pytest.raises(EmptyCommandError):
        intake.process_intake("")

    with pytest.raises(EmptyCommandError):
        intake.process_intake("   \n\t  ")


def test_mission_intake_invalid_explicit_workspace_raises(tmp_path):
    intake = MissionIntake()
    invalid_ws = tmp_path / "non_existent_workspace_dir_12345"
    with pytest.raises(WorkspaceUnavailableError):
        intake.process_intake("Create REST API", explicit_workspace=invalid_ws)


def test_mission_intake_parse_cli_command():
    intake = MissionIntake()
    req = intake.parse_cli_command(["Refactor", "authentication"])
    assert req.normalized_command == "Refactor authentication"
    assert req.metadata["primary_command"] == "Refactor"


def test_cli_backward_compatibility():
    assert "doctor" in REGISTERED_CLI_COMMANDS
    assert "workspace" in REGISTERED_CLI_COMMANDS
    assert "history" in REGISTERED_CLI_COMMANDS
    assert "events" in REGISTERED_CLI_COMMANDS
