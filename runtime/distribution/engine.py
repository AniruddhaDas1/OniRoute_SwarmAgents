"""Platform Distribution Engine for Phase P6.D4.

First-run experience, configuration management, platform detection,
and distribution preparation. Consumes existing CLI and Runtime APIs
without modifying engine architecture.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

# ── Version ───────────────────────────────────────────────────────────────

ONIROUTE_VERSION = "1.2.0"
ONIROUTE_CODENAME = "Swarm Intelligence"

# ── Data Contracts ────────────────────────────────────────────────────────


class PlatformInfo(BaseModel):
    """Immutable platform detection result."""

    model_config = ConfigDict(frozen=True)

    os_name: str = Field(..., description="Operating system name")
    os_version: str = Field(..., description="Operating system version")
    architecture: str = Field(..., description="CPU architecture")
    python_version: str = Field(..., description="Python interpreter version")
    python_path: str = Field(..., description="Python executable path")
    git_available: bool = Field(default=False, description="Git is available")
    git_version: str = Field(default="", description="Git version string")
    docker_available: bool = Field(default=False, description="Docker is available")
    pipx_available: bool = Field(default=False, description="pipx is available")
    brew_available: bool = Field(default=False, description="Homebrew is available")
    npm_available: bool = Field(default=False, description="npm is available")
    mcp_available: bool = Field(default=False, description="MCP tools detected")
    timestamp: str = Field(..., description="ISO-8601 detection timestamp")


class InitializationResult(BaseModel):
    """Immutable result of oniroute init."""

    model_config = ConfigDict(frozen=True)

    success: bool = Field(..., description="True if initialization succeeded")
    workspace_root: str = Field(..., description="Initialized workspace path")
    config_path: str = Field(..., description="Created configuration file path")
    platform: PlatformInfo = Field(..., description="Detected platform information")
    checks_passed: List[str] = Field(default_factory=list, description="Passed checks")
    checks_failed: List[str] = Field(default_factory=list, description="Failed checks")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking warnings")
    message: str = Field(default="", description="Human-readable result message")
    latency_ms: float = Field(default=0.0, description="Initialization latency")
    timestamp: str = Field(..., description="ISO-8601 timestamp")


class OniRouteConfig(BaseModel):
    """OniRoute configuration schema."""

    version: str = Field(default=ONIROUTE_VERSION, description="Configuration schema version")
    workspace_root: str = Field(default=".", description="Default workspace root")
    logging_level: str = Field(default="INFO", description="Log level")
    validation_mode: str = Field(default="standard", description="Validation mode")
    providers: Dict[str, Any] = Field(default_factory=dict, description="LLM provider configuration")
    mcp: Dict[str, Any] = Field(default_factory=dict, description="MCP tool configuration")
    secrets: Dict[str, str] = Field(default_factory=dict, description="Secrets (env var references)")
    review_strategy: str = Field(default="cross-agent-5-profile-review", description="Default review strategy")
    healing_strategy: str = Field(default="automated-self-healing", description="Default healing strategy")
    max_concurrent_missions: int = Field(default=3, description="Max concurrent missions")
    default_quality_threshold: float = Field(default=8.0, description="Default quality threshold")
    telemetry_enabled: bool = Field(default=False, description="Telemetry opt-in")


class ConfigValidationResult(BaseModel):
    """Immutable configuration validation result."""

    model_config = ConfigDict(frozen=True)

    valid: bool = Field(..., description="True if configuration is valid")
    config_path: str = Field(..., description="Validated configuration file path")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    resolved_values: Dict[str, Any] = Field(default_factory=dict, description="Resolved config values")
    timestamp: str = Field(..., description="ISO-8601 timestamp")


# ── Platform Detection ────────────────────────────────────────────────────


class PlatformDetector:
    """Detects platform capabilities for distribution compatibility."""

    def detect(self) -> PlatformInfo:
        """Detect current platform information."""
        git_ok, git_ver = self._check_binary("git", "--version")
        docker_ok, _ = self._check_binary("docker", "--version")
        pipx_ok, _ = self._check_binary("pipx", "--version")
        brew_ok, _ = self._check_binary("brew", "--version")
        npm_ok, _ = self._check_binary("npm", "--version")

        # Check MCP availability
        mcp_ok = self._check_mcp()

        return PlatformInfo(
            os_name=platform.system(),
            os_version=platform.version(),
            architecture=platform.machine(),
            python_version=platform.python_version(),
            python_path=sys.executable,
            git_available=git_ok,
            git_version=git_ver,
            docker_available=docker_ok,
            pipx_available=pipx_ok,
            brew_available=brew_ok,
            npm_available=npm_ok,
            mcp_available=mcp_ok,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _check_binary(self, cmd: str, flag: str) -> tuple[bool, str]:
        """Check if a binary is available on PATH."""
        try:
            result = subprocess.run(
                [cmd, flag], capture_output=True, text=True, timeout=5
            )
            version_line = result.stdout.strip().split("\n")[0] if result.stdout else ""
            return result.returncode == 0, version_line
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False, ""

    def _check_mcp(self) -> bool:
        """Check if MCP tools are available (config or env)."""
        mcp_config = Path.home() / ".config" / "mcp"
        if mcp_config.exists():
            return True
        return bool(os.environ.get("MCP_SERVER_URL") or os.environ.get("MCP_CONFIG"))


# ── Configuration Manager ─────────────────────────────────────────────────


class ConfigurationManager:
    """Manages global and per-project OniRoute configuration."""

    GLOBAL_CONFIG_DIR = Path.home() / ".config" / "oniroute"
    GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.yaml"

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    def get_project_config_path(self) -> Path:
        """Get per-project configuration file path."""
        return self.workspace_root / ".oniroute" / "config.yaml"

    def load_config(self) -> OniRouteConfig:
        """Load merged configuration (global → project → env overrides)."""
        config_data: Dict[str, Any] = {}

        # 1. Load global config
        if self.GLOBAL_CONFIG_FILE.exists():
            try:
                raw = yaml.safe_load(self.GLOBAL_CONFIG_FILE.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    config_data.update(raw)
            except Exception:
                pass

        # 2. Load project config (overrides global)
        project_config = self.get_project_config_path()
        if project_config.exists():
            try:
                raw = yaml.safe_load(project_config.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    config_data.update(raw)
            except Exception:
                pass

        # 3. Apply environment overrides
        env_overrides = {
            "ONIROUTE_LOG_LEVEL": "logging_level",
            "ONIROUTE_VALIDATION_MODE": "validation_mode",
            "ONIROUTE_REVIEW_STRATEGY": "review_strategy",
            "ONIROUTE_MAX_CONCURRENT": "max_concurrent_missions",
            "ONIROUTE_QUALITY_THRESHOLD": "default_quality_threshold",
            "ONIROUTE_TELEMETRY": "telemetry_enabled",
        }
        for env_key, config_key in env_overrides.items():
            val = os.environ.get(env_key)
            if val is not None:
                if config_key in ("max_concurrent_missions",):
                    config_data[config_key] = int(val)
                elif config_key in ("default_quality_threshold",):
                    config_data[config_key] = float(val)
                elif config_key in ("telemetry_enabled",):
                    config_data[config_key] = val.lower() in ("true", "1", "yes")
                else:
                    config_data[config_key] = val

        # 4. Resolve secrets from environment
        secrets = config_data.get("secrets", {})
        if isinstance(secrets, dict):
            for key, ref in secrets.items():
                if isinstance(ref, str) and ref.startswith("$"):
                    env_val = os.environ.get(ref.lstrip("$"), "")
                    secrets[key] = env_val
            config_data["secrets"] = secrets

        return OniRouteConfig(**{k: v for k, v in config_data.items() if k in OniRouteConfig.model_fields})

    def save_config(self, config: OniRouteConfig, scope: str = "project") -> Path:
        """Save configuration to file.

        Args:
            config: Configuration to save.
            scope: 'global' or 'project'.

        Returns:
            Path: Saved configuration file path.
        """
        if scope == "global":
            target = self.GLOBAL_CONFIG_FILE
        else:
            target = self.get_project_config_path()

        target.parent.mkdir(parents=True, exist_ok=True)
        data = config.model_dump(mode="json")
        # Never persist resolved secrets to disk
        data.pop("secrets", None)

        target.write_text(
            yaml.safe_dump(data, default_flow_style=False, sort_keys=True),
            encoding="utf-8",
        )
        return target

    def validate_config(self) -> ConfigValidationResult:
        """Validate the merged configuration."""
        errors: List[str] = []
        warnings: List[str] = []

        try:
            config = self.load_config()
        except Exception as exc:
            return ConfigValidationResult(
                valid=False,
                config_path=str(self.get_project_config_path()),
                errors=[f"Configuration parse error: {exc}"],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Validate fields
        if config.max_concurrent_missions < 1:
            errors.append("max_concurrent_missions must be >= 1")
        if config.max_concurrent_missions > 10:
            warnings.append("max_concurrent_missions > 10 may degrade performance")

        if config.default_quality_threshold < 0 or config.default_quality_threshold > 10:
            errors.append("default_quality_threshold must be between 0 and 10")

        if config.logging_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            warnings.append(f"Unusual logging_level: {config.logging_level}")

        resolved = config.model_dump(mode="json")

        return ConfigValidationResult(
            valid=len(errors) == 0,
            config_path=str(self.get_project_config_path()),
            errors=errors,
            warnings=warnings,
            resolved_values=resolved,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_config_value(self, key: str) -> Any:
        """Get a single configuration value."""
        config = self.load_config()
        return getattr(config, key, None)

    def set_config_value(self, key: str, value: Any, scope: str = "project") -> Path:
        """Set a single configuration value."""
        config = self.load_config()
        data = config.model_dump(mode="json")
        data[key] = value
        updated = OniRouteConfig(**{k: v for k, v in data.items() if k in OniRouteConfig.model_fields})
        return self.save_config(updated, scope=scope)


# ── Initialization Engine ─────────────────────────────────────────────────


class InitializationEngine:
    """First-run initialization engine for oniroute init."""

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.detector = PlatformDetector()
        self.config_manager = ConfigurationManager(self.workspace_root)

    def initialize(self) -> InitializationResult:
        """Run full first-run initialization.

        Returns:
            InitializationResult: Immutable initialization result.
        """
        start = time.perf_counter()
        checks_passed: List[str] = []
        checks_failed: List[str] = []
        warnings: List[str] = []

        # 1. Detect platform
        plat = self.detector.detect()

        # 2. Verify Python
        py_major, py_minor = sys.version_info[:2]
        if py_major >= 3 and py_minor >= 12:
            checks_passed.append(f"Python {plat.python_version} (>= 3.12)")
        else:
            checks_failed.append(f"Python {plat.python_version} — requires >= 3.12")

        # 3. Verify Git
        if plat.git_available:
            checks_passed.append(f"Git: {plat.git_version}")
        else:
            checks_failed.append("Git not found — required for workspace operations")

        # 4. Verify package managers
        if plat.pipx_available:
            checks_passed.append("pipx available")
        else:
            warnings.append("pipx not found — recommended for global install")

        if plat.brew_available:
            checks_passed.append("Homebrew available")
        elif plat.os_name == "Darwin":
            warnings.append("Homebrew not found — recommended on macOS")

        if plat.docker_available:
            checks_passed.append("Docker available")
        else:
            warnings.append("Docker not found — optional for containerized execution")

        # 5. Check MCP
        if plat.mcp_available:
            checks_passed.append("MCP tools detected")
        else:
            warnings.append("MCP not configured — some features may be unavailable")

        # 6. Create workspace config
        oniroute_dir = self.workspace_root / ".oniroute"
        oniroute_dir.mkdir(parents=True, exist_ok=True)
        (oniroute_dir / "sessions").mkdir(exist_ok=True)
        (oniroute_dir / "traces").mkdir(exist_ok=True)
        (oniroute_dir / "logs").mkdir(exist_ok=True)
        (oniroute_dir / "history").mkdir(exist_ok=True)
        (oniroute_dir / "artifacts").mkdir(exist_ok=True)
        checks_passed.append("Workspace directories created")

        # 7. Generate default configuration
        default_config = OniRouteConfig(
            workspace_root=str(self.workspace_root),
        )
        config_path = self.config_manager.save_config(default_config, scope="project")
        checks_passed.append(f"Configuration created: {config_path}")

        # 8. Generate global config if not exists
        if not ConfigurationManager.GLOBAL_CONFIG_FILE.exists():
            try:
                self.config_manager.save_config(default_config, scope="global")
                checks_passed.append("Global configuration created")
            except Exception:
                warnings.append("Could not create global configuration")

        success = len(checks_failed) == 0
        latency_ms = (time.perf_counter() - start) * 1000.0

        message = (
            "OniRoute initialized successfully! Run 'oniroute doctor' to verify."
            if success
            else f"Initialization completed with {len(checks_failed)} issue(s). Fix them and re-run 'oniroute init'."
        )

        return InitializationResult(
            success=success,
            workspace_root=str(self.workspace_root),
            config_path=str(config_path),
            platform=plat,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            warnings=warnings,
            message=message,
            latency_ms=round(latency_ms, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# ── Distribution Preparer ─────────────────────────────────────────────────


class DistributionPreparer:
    """Prepares distribution artifacts for PyPI, Homebrew, Docker, and executables."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()

    def get_distribution_manifest(self) -> Dict[str, Any]:
        """Generate distribution manifest describing all targets."""
        return {
            "version": ONIROUTE_VERSION,
            "codename": ONIROUTE_CODENAME,
            "targets": {
                "pypi": {
                    "package": "oniroute-swarmagents",
                    "entry_point": "oniroute = cli.main:main",
                    "install": "pip install oniroute-swarmagents",
                    "install_pipx": "pipx install oniroute-swarmagents",
                },
                "homebrew": {
                    "formula": "Formula/oniroute.rb",
                    "tap": "oniroute/tap",
                    "install": "brew install oniroute/tap/oniroute",
                },
                "docker": {
                    "image": "oniroute/oniroute:1.2.0",
                    "dockerfile": "Dockerfile",
                    "run": "docker run --rm -v $(pwd):/workspace oniroute/oniroute:1.2.0 build 'my app'",
                },
                "standalone": {
                    "macos_arm64": "oniroute-1.2.0-macos-arm64",
                    "macos_x64": "oniroute-1.2.0-macos-x64",
                    "linux_x64": "oniroute-1.2.0-linux-x64",
                    "windows_x64": "oniroute-1.2.0-windows-x64.exe",
                    "build_tool": "PyInstaller",
                },
                "github_release": {
                    "tag": "v1.2.0",
                    "assets": [
                        "oniroute-1.2.0-macos-arm64",
                        "oniroute-1.2.0-macos-x64",
                        "oniroute-1.2.0-linux-x64",
                        "oniroute-1.2.0-windows-x64.exe",
                        "oniroute-swarmagents-1.2.0.tar.gz",
                        "oniroute-swarmagents-1.2.0-py3-none-any.whl",
                    ],
                },
            },
            "platforms": {
                "macos": {"min_version": "12.0", "architectures": ["arm64", "x86_64"]},
                "linux": {"distributions": ["Ubuntu 22.04+", "Debian 12+", "Fedora 38+", "Arch"], "architectures": ["x86_64", "aarch64"]},
                "windows": {"min_version": "10", "architectures": ["x86_64"]},
            },
            "requirements": {
                "python": ">=3.12",
                "git": ">=2.30",
            },
        }
