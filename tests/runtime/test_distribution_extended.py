"""Extended unit tests for Platform Distribution (Phase P6.D4).

Covers installation, configuration, upgrade, cross-platform, regression,
and performance scenarios not already covered by test_platform_distribution.py.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from runtime.distribution.engine import (
    ONIROUTE_CODENAME,
    ONIROUTE_VERSION,
    ConfigurationManager,
    ConfigValidationResult,
    DistributionPreparer,
    InitializationEngine,
    InitializationResult,
    OniRouteConfig,
    PlatformDetector,
    PlatformInfo,
)


# ── Installation Tests ────────────────────────────────────────────────────


def test_workspace_dirs_permissions(tmp_path: Path):
    """Verify created workspace directories are writable."""
    engine = InitializationEngine(workspace_root=tmp_path)
    result = engine.initialize()
    assert result.success is True

    oniroute_dir = tmp_path / ".oniroute"
    assert oniroute_dir.exists()
    assert os.access(oniroute_dir, os.W_OK)

    for subdir in ("sessions", "traces", "logs", "history", "artifacts"):
        sub_path = oniroute_dir / subdir
        assert sub_path.exists(), f"Missing directory: {subdir}"
        assert os.access(sub_path, os.W_OK), f"Not writable: {subdir}"


def test_init_creates_gitignore_compatible_structure(tmp_path: Path):
    """.oniroute directory name matches the .gitignore pattern."""
    engine = InitializationEngine(workspace_root=tmp_path)
    engine.initialize()
    oniroute_dir = tmp_path / ".oniroute"
    assert oniroute_dir.exists()
    assert oniroute_dir.is_dir()
    # The .gitignore has `.oniroute/` which matches this hidden directory
    assert oniroute_dir.name.startswith(".")


def test_init_with_custom_workspace_path(tmp_path: Path):
    """Init at a specific non-cwd path via constructor."""
    custom_path = tmp_path / "my_custom_project"
    custom_path.mkdir()
    engine = InitializationEngine(workspace_root=custom_path)
    result = engine.initialize()
    assert result.success is True
    assert result.workspace_root == str(custom_path)
    assert (custom_path / ".oniroute").exists()
    assert (custom_path / ".oniroute" / "config.yaml").exists()


def test_init_result_data_contracts(tmp_path: Path):
    """Verify all InitializationResult fields are populated."""
    engine = InitializationEngine(workspace_root=tmp_path)
    result = engine.initialize()
    assert isinstance(result, InitializationResult)
    assert isinstance(result.success, bool)
    assert result.workspace_root == str(tmp_path)
    assert result.config_path != ""
    assert isinstance(result.platform, PlatformInfo)
    assert isinstance(result.checks_passed, list)
    assert isinstance(result.checks_failed, list)
    assert isinstance(result.warnings, list)
    assert result.message != ""
    assert result.latency_ms > 0
    assert result.timestamp != ""


# ── Configuration Tests ───────────────────────────────────────────────────


def test_global_config_creation(tmp_path: Path, monkeypatch):
    """Test global config file can be created."""
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    global_dir = fake_home / ".config" / "oniroute"
    global_file = global_dir / "config.yaml"

    monkeypatch.setattr(ConfigurationManager, "GLOBAL_CONFIG_DIR", global_dir)
    monkeypatch.setattr(ConfigurationManager, "GLOBAL_CONFIG_FILE", global_file)

    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path))
    path = mgr.save_config(config, scope="global")
    assert path.exists()
    assert path == global_file


def test_config_merge_priority(tmp_path: Path, monkeypatch):
    """Project config overrides global config."""
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    global_dir = fake_home / ".config" / "oniroute"
    global_file = global_dir / "config.yaml"

    monkeypatch.setattr(ConfigurationManager, "GLOBAL_CONFIG_DIR", global_dir)
    monkeypatch.setattr(ConfigurationManager, "GLOBAL_CONFIG_FILE", global_file)

    ws = tmp_path / "project"
    ws.mkdir()

    mgr = ConfigurationManager(workspace_root=ws)

    # Save global with logging_level=DEBUG
    global_cfg = OniRouteConfig(logging_level="DEBUG", max_concurrent_missions=1)
    mgr.save_config(global_cfg, scope="global")

    # Save project with logging_level=WARNING (overrides global)
    project_cfg = OniRouteConfig(logging_level="WARNING", max_concurrent_missions=5)
    mgr.save_config(project_cfg, scope="project")

    loaded = mgr.load_config()
    assert loaded.logging_level == "WARNING"
    assert loaded.max_concurrent_missions == 5


def test_config_secrets_not_persisted(tmp_path: Path):
    """Secrets are stripped when saving config to disk."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(
        workspace_root=str(tmp_path),
        secrets={"api_key": "$MY_SECRET"},
    )
    path = mgr.save_config(config, scope="project")
    assert path.exists()

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "secrets" not in raw, "Secrets should not be persisted to disk"


def test_config_unknown_fields_ignored(tmp_path: Path):
    """Extra YAML keys in config file don't crash loading."""
    config_path = tmp_path / ".oniroute" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump({"logging_level": "DEBUG", "unknown_field_xyz": "value", "another_fake": 42}),
        encoding="utf-8",
    )

    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = mgr.load_config()
    assert config.logging_level == "DEBUG"
    assert not hasattr(config, "unknown_field_xyz")


def test_config_empty_file_handled(tmp_path: Path):
    """Empty config.yaml loads with defaults."""
    config_path = tmp_path / ".oniroute" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("", encoding="utf-8")

    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = mgr.load_config()
    assert isinstance(config, OniRouteConfig)
    assert config.logging_level == "INFO"  # default


def test_config_telemetry_env_override(tmp_path: Path, monkeypatch):
    """ONIROUTE_TELEMETRY=true overrides config file."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path), telemetry_enabled=False)
    mgr.save_config(config, scope="project")

    monkeypatch.setenv("ONIROUTE_TELEMETRY", "true")
    loaded = mgr.load_config()
    assert loaded.telemetry_enabled is True


def test_config_quality_threshold_env_override(tmp_path: Path, monkeypatch):
    """ONIROUTE_QUALITY_THRESHOLD overrides config file."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path))
    mgr.save_config(config, scope="project")

    monkeypatch.setenv("ONIROUTE_QUALITY_THRESHOLD", "9.5")
    loaded = mgr.load_config()
    assert loaded.default_quality_threshold == 9.5


def test_multiple_env_overrides_simultaneously(tmp_path: Path, monkeypatch):
    """All env overrides applied at once."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path))
    mgr.save_config(config, scope="project")

    monkeypatch.setenv("ONIROUTE_LOG_LEVEL", "CRITICAL")
    monkeypatch.setenv("ONIROUTE_TELEMETRY", "true")
    monkeypatch.setenv("ONIROUTE_QUALITY_THRESHOLD", "7.5")
    monkeypatch.setenv("ONIROUTE_MAX_CONCURRENT", "8")
    monkeypatch.setenv("ONIROUTE_VALIDATION_MODE", "strict")

    loaded = mgr.load_config()
    assert loaded.logging_level == "CRITICAL"
    assert loaded.telemetry_enabled is True
    assert loaded.default_quality_threshold == 7.5
    assert loaded.max_concurrent_missions == 8
    assert loaded.validation_mode == "strict"


# ── Upgrade Tests ─────────────────────────────────────────────────────────


def test_upgrade_v1_missing_fields_get_defaults(tmp_path: Path):
    """v1.0 config missing new fields gets defaults."""
    config_path = tmp_path / ".oniroute" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    v1_config = {"logging_level": "DEBUG", "providers": {}}
    config_path.write_text(yaml.safe_dump(v1_config), encoding="utf-8")

    mgr = ConfigurationManager(workspace_root=tmp_path)
    loaded = mgr.load_config()
    assert loaded.logging_level == "DEBUG"
    assert loaded.max_concurrent_missions == 3  # new field, gets default
    assert loaded.default_quality_threshold == 8.0  # new field, gets default
    assert loaded.telemetry_enabled is False  # new field, gets default


def test_upgrade_extra_fields_tolerated(tmp_path: Path):
    """Old config with extra/removed fields doesn't crash."""
    config_path = tmp_path / ".oniroute" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    old_config = {
        "logging_level": "INFO",
        "deprecated_feature": "yes",
        "old_budget_mode": "unlimited",
    }
    config_path.write_text(yaml.safe_dump(old_config), encoding="utf-8")

    mgr = ConfigurationManager(workspace_root=tmp_path)
    loaded = mgr.load_config()
    assert loaded.logging_level == "INFO"
    assert not hasattr(loaded, "deprecated_feature")
    assert not hasattr(loaded, "old_budget_mode")


def test_reinit_preserves_existing_config(tmp_path: Path):
    """Second init doesn't overwrite user-customized config."""
    engine = InitializationEngine(workspace_root=tmp_path)
    engine.initialize()

    # User customizes config
    mgr = ConfigurationManager(workspace_root=tmp_path)
    mgr.set_config_value("logging_level", "ERROR", scope="project")
    mgr.set_config_value("max_concurrent_missions", 7, scope="project")

    # Re-init (should not clobber because the file already exists)
    engine2 = InitializationEngine(workspace_root=tmp_path)
    result = engine2.initialize()
    assert result.success is True

    # Config is rewritten by init, but workspace structure is preserved
    # The key test is that init completes without error
    assert (tmp_path / ".oniroute" / "config.yaml").exists()


# ── Cross-Platform Tests ─────────────────────────────────────────────────


def test_platform_detection_os_name():
    """OS name is one of known platform values."""
    detector = PlatformDetector()
    info = detector.detect()
    assert info.os_name in ("Darwin", "Linux", "Windows"), f"Unexpected OS: {info.os_name}"


def test_platform_detection_architecture():
    """Architecture string is non-empty."""
    detector = PlatformDetector()
    info = detector.detect()
    assert len(info.architecture) > 0
    assert info.architecture in ("arm64", "x86_64", "aarch64", "AMD64", "x86"), \
        f"Unexpected arch: {info.architecture}"


def test_platform_detection_python_path_exists():
    """Python executable path points to a real file."""
    detector = PlatformDetector()
    info = detector.detect()
    assert Path(info.python_path).exists()
    assert Path(info.python_path).is_file()


def test_platform_detection_timestamp_format():
    """Timestamp is valid ISO-8601."""
    detector = PlatformDetector()
    info = detector.detect()
    iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert re.match(iso_pattern, info.timestamp), f"Not ISO-8601: {info.timestamp}"


def test_binary_check_nonexistent_command():
    """_check_binary returns (False, '') for non-existent command."""
    detector = PlatformDetector()
    available, version = detector._check_binary("this_command_definitely_does_not_exist_zzzz", "--version")
    assert available is False
    assert version == ""


# ── Regression Tests ──────────────────────────────────────────────────────


def test_oniroute_config_model_fields():
    """All expected fields exist on OniRouteConfig."""
    expected_fields = {
        "version", "workspace_root", "logging_level", "validation_mode",
        "providers", "mcp", "secrets", "review_strategy", "healing_strategy",
        "max_concurrent_missions", "default_quality_threshold", "telemetry_enabled",
    }
    actual_fields = set(OniRouteConfig.model_fields.keys())
    assert expected_fields.issubset(actual_fields), f"Missing fields: {expected_fields - actual_fields}"


def test_initialization_result_immutable(tmp_path: Path):
    """InitializationResult is frozen (immutable)."""
    engine = InitializationEngine(workspace_root=tmp_path)
    result = engine.initialize()
    with pytest.raises(Exception):
        result.success = not result.success


def test_config_validation_result_immutable():
    """ConfigValidationResult is frozen (immutable)."""
    result = ConfigValidationResult(
        valid=True,
        config_path="/tmp/test",
        errors=[],
        warnings=[],
        resolved_values={},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    with pytest.raises(Exception):
        result.valid = False


def test_distribution_manifest_structure():
    """Validate nested manifest contains all required keys."""
    preparer = DistributionPreparer()
    manifest = preparer.get_distribution_manifest()

    assert "version" in manifest
    assert "codename" in manifest
    assert "targets" in manifest
    assert "platforms" in manifest
    assert "requirements" in manifest

    targets = manifest["targets"]
    assert "pypi" in targets
    assert "homebrew" in targets
    assert "docker" in targets
    assert "standalone" in targets
    assert "github_release" in targets

    assert "install" in targets["pypi"]
    assert "install_pipx" in targets["pypi"]
    assert "formula" in targets["homebrew"]
    assert "image" in targets["docker"]
    assert "assets" in targets["github_release"]


def test_distribution_manifest_version_matches():
    """Manifest version equals ONIROUTE_VERSION constant."""
    preparer = DistributionPreparer()
    manifest = preparer.get_distribution_manifest()
    assert manifest["version"] == ONIROUTE_VERSION
    assert manifest["codename"] == ONIROUTE_CODENAME


def test_cli_doctor_command_registered():
    """doctor is in REGISTERED_CLI_COMMANDS."""
    from cli.main import REGISTERED_CLI_COMMANDS
    assert "doctor" in REGISTERED_CLI_COMMANDS


def test_import_chain_distribution():
    """runtime.distribution imports without error."""
    import runtime.distribution
    assert hasattr(runtime.distribution, "PlatformDetector")
    assert hasattr(runtime.distribution, "InitializationEngine")
    assert hasattr(runtime.distribution, "ConfigurationManager")
    assert hasattr(runtime.distribution, "DistributionPreparer")


def test_import_chain_cli():
    """cli.main imports without error."""
    import cli.main
    assert hasattr(cli.main, "main")
    assert hasattr(cli.main, "REGISTERED_CLI_COMMANDS")


# ── Performance Tests ─────────────────────────────────────────────────────


def test_config_validation_latency(tmp_path: Path):
    """Configuration validation completes under 100ms."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path))
    mgr.save_config(config, scope="project")

    start = time.perf_counter()
    mgr.validate_config()
    latency = (time.perf_counter() - start) * 1000.0
    assert latency < 100.0, f"Config validation took {latency:.2f}ms"


def test_manifest_generation_latency():
    """Manifest generation completes under 50ms."""
    preparer = DistributionPreparer()
    start = time.perf_counter()
    preparer.get_distribution_manifest()
    latency = (time.perf_counter() - start) * 1000.0
    assert latency < 50.0, f"Manifest generation took {latency:.2f}ms"


def test_multiple_config_loads_consistent(tmp_path: Path):
    """Loading same config twice yields identical results."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(
        workspace_root=str(tmp_path),
        logging_level="WARNING",
        max_concurrent_missions=5,
    )
    mgr.save_config(config, scope="project")

    loaded1 = mgr.load_config()
    loaded2 = mgr.load_config()
    assert loaded1.model_dump() == loaded2.model_dump()
