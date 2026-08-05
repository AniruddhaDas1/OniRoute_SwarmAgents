"""Unit tests for Platform Distribution (Phase P6.D4).

Tests installation, configuration, platform detection, upgrade,
cross-platform compatibility, and CLI regression.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import yaml

from runtime.distribution.engine import (
    ONIROUTE_VERSION,
    ONIROUTE_CODENAME,
    ConfigurationManager,
    ConfigValidationResult,
    DistributionPreparer,
    InitializationEngine,
    InitializationResult,
    OniRouteConfig,
    PlatformDetector,
    PlatformInfo,
)


# ── Platform Detection Tests ──────────────────────────────────────────────

def test_platform_detection():
    """Test that platform detection returns valid PlatformInfo."""
    detector = PlatformDetector()
    info = detector.detect()
    assert isinstance(info, PlatformInfo)
    assert info.os_name != ""
    assert info.python_version != ""
    assert info.python_path != ""
    assert info.architecture != ""
    assert info.timestamp != ""


def test_platform_info_frozen():
    """Test that PlatformInfo is immutable."""
    detector = PlatformDetector()
    info = detector.detect()
    with pytest.raises(Exception):
        info.os_name = "modified"


# ── Installation / Initialization Tests ───────────────────────────────────

def test_initialization(tmp_path: Path):
    """Test that oniroute init creates workspace structure."""
    engine = InitializationEngine(workspace_root=tmp_path)
    result = engine.initialize()
    assert isinstance(result, InitializationResult)
    assert result.success is True
    assert result.workspace_root == str(tmp_path)
    assert result.config_path != ""
    assert len(result.checks_passed) > 0
    assert result.latency_ms > 0

    # Verify workspace directories
    oniroute_dir = tmp_path / ".oniroute"
    assert oniroute_dir.exists()
    assert (oniroute_dir / "sessions").exists()
    assert (oniroute_dir / "traces").exists()
    assert (oniroute_dir / "logs").exists()
    assert (oniroute_dir / "history").exists()
    assert (oniroute_dir / "artifacts").exists()
    assert (oniroute_dir / "config.yaml").exists()


def test_initialization_idempotent(tmp_path: Path):
    """Test that running init twice doesn't break anything."""
    engine = InitializationEngine(workspace_root=tmp_path)
    result1 = engine.initialize()
    result2 = engine.initialize()
    assert result1.success is True
    assert result2.success is True


# ── Configuration Tests ───────────────────────────────────────────────────

def test_default_config():
    """Test OniRouteConfig default values."""
    config = OniRouteConfig()
    assert config.version == ONIROUTE_VERSION
    assert config.logging_level == "INFO"
    assert config.validation_mode == "standard"
    assert config.max_concurrent_missions == 3
    assert config.default_quality_threshold == 8.0
    assert config.telemetry_enabled is False


def test_config_save_and_load(tmp_path: Path):
    """Test saving and loading configuration."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(
        workspace_root=str(tmp_path),
        logging_level="DEBUG",
        max_concurrent_missions=5,
    )
    path = mgr.save_config(config, scope="project")
    assert path.exists()

    loaded = mgr.load_config()
    assert loaded.logging_level == "DEBUG"
    assert loaded.max_concurrent_missions == 5


def test_config_env_overrides(tmp_path: Path, monkeypatch):
    """Test environment variable configuration overrides."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path))
    mgr.save_config(config, scope="project")

    monkeypatch.setenv("ONIROUTE_LOG_LEVEL", "ERROR")
    monkeypatch.setenv("ONIROUTE_MAX_CONCURRENT", "7")

    loaded = mgr.load_config()
    assert loaded.logging_level == "ERROR"
    assert loaded.max_concurrent_missions == 7


def test_config_validation_valid(tmp_path: Path):
    """Test configuration validation with valid config."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path))
    mgr.save_config(config, scope="project")

    result = mgr.validate_config()
    assert isinstance(result, ConfigValidationResult)
    assert result.valid is True
    assert len(result.errors) == 0


def test_config_validation_invalid(tmp_path: Path):
    """Test configuration validation with invalid values."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    # Write invalid config directly
    config_path = tmp_path / ".oniroute" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump({"max_concurrent_missions": -1, "default_quality_threshold": 15}),
        encoding="utf-8",
    )

    result = mgr.validate_config()
    assert result.valid is False
    assert len(result.errors) > 0


def test_config_set_and_get(tmp_path: Path):
    """Test setting and getting individual config values."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path))
    mgr.save_config(config, scope="project")

    mgr.set_config_value("logging_level", "WARNING", scope="project")
    val = mgr.get_config_value("logging_level")
    assert val == "WARNING"


def test_secrets_resolution(tmp_path: Path, monkeypatch):
    """Test secrets resolved from environment variables."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config_path = tmp_path / ".oniroute" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump({"secrets": {"api_key": "$MY_SECRET_KEY"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("MY_SECRET_KEY", "sk-test-12345")
    loaded = mgr.load_config()
    assert loaded.secrets.get("api_key") == "sk-test-12345"


# ── Upgrade Compatibility Tests ───────────────────────────────────────────

def test_upgrade_preserves_config(tmp_path: Path):
    """Test that v1.0 config is compatible with v1.2 loading."""
    config_path = tmp_path / ".oniroute" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    # Simulate v1.0 config
    v1_config = {"logging_level": "DEBUG", "validation_mode": "standard", "providers": {}}
    config_path.write_text(yaml.safe_dump(v1_config), encoding="utf-8")

    mgr = ConfigurationManager(workspace_root=tmp_path)
    loaded = mgr.load_config()
    assert loaded.logging_level == "DEBUG"
    assert loaded.max_concurrent_missions == 3  # New field gets default


# ── Distribution Tests ────────────────────────────────────────────────────

def test_distribution_manifest():
    """Test distribution manifest contains all targets."""
    preparer = DistributionPreparer()
    manifest = preparer.get_distribution_manifest()

    assert manifest["version"] == ONIROUTE_VERSION
    assert "pypi" in manifest["targets"]
    assert "homebrew" in manifest["targets"]
    assert "docker" in manifest["targets"]
    assert "standalone" in manifest["targets"]
    assert "github_release" in manifest["targets"]
    assert "macos" in manifest["platforms"]
    assert "linux" in manifest["platforms"]
    assert "windows" in manifest["platforms"]


# ── Cross-Platform Tests ─────────────────────────────────────────────────

def test_version_constant():
    """Test version string format."""
    parts = ONIROUTE_VERSION.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_codename_set():
    """Test codename is non-empty."""
    assert ONIROUTE_CODENAME != ""


# ── CLI Regression Tests ─────────────────────────────────────────────────

def test_cli_distribution_commands_registered():
    """Test that init, config, update, version CLI commands are registered."""
    from cli.main import REGISTERED_CLI_COMMANDS
    assert "init" in REGISTERED_CLI_COMMANDS
    assert "config" in REGISTERED_CLI_COMMANDS
    assert "update" in REGISTERED_CLI_COMMANDS
    assert "version" in REGISTERED_CLI_COMMANDS


# ── Performance Tests ─────────────────────────────────────────────────────

def test_initialization_latency(tmp_path: Path):
    """Test that initialization completes under 500ms."""
    engine = InitializationEngine(workspace_root=tmp_path)
    result = engine.initialize()
    assert result.latency_ms < 500.0


def test_startup_latency():
    """Test that platform detection completes under 10 seconds."""
    start = time.perf_counter()
    detector = PlatformDetector()
    detector.detect()
    latency = (time.perf_counter() - start) * 1000.0
    assert latency < 10000.0  # 10s max (binaries may timeout)


def test_config_load_latency(tmp_path: Path):
    """Test that configuration loading completes under 50ms."""
    mgr = ConfigurationManager(workspace_root=tmp_path)
    config = OniRouteConfig(workspace_root=str(tmp_path))
    mgr.save_config(config, scope="project")

    start = time.perf_counter()
    mgr.load_config()
    latency = (time.perf_counter() - start) * 1000.0
    assert latency < 50.0
