# Migration Guide: OniRoute v1.0.0 to v1.2.0

This guide assists users and administrators in upgrading from OniRoute v1.0.0 to v1.2.0.

---

## Overview of Changes

OniRoute v1.2.0 is a **zero-breaking-change release**. All existing v1.0.0 workflows, agents, skills, and configuration keys remain 100% compatible.

v1.2.0 introduces the **Platform Distribution Layer** and **First-Run Experience**:
- New CLI commands: `init`, `config`, `update`, `version`
- Automatic platform detection for OS, Python, Git, Docker, and MCP
- Hierarchical configuration (global `~/.config/oniroute/config.yaml` and project `.oniroute/config.yaml`)
- Workspace storage directories in `.oniroute/`

---

## Step-by-Step Upgrade Procedure

### 1. Upgrade Package / Binary

Select the upgrade path corresponding to your installation method:

#### pipx (Recommended)
```bash
pipx upgrade oniroute-swarmagents
```

#### pip
```bash
pip install --upgrade oniroute-swarmagents
```

#### Homebrew (macOS / Linux)
```bash
brew update
brew upgrade oniroute
```

#### Docker
```bash
docker pull oniroute/oniroute:1.2.0
```

---

### 2. Initialize Existing Workspaces

Run `oniroute init` inside your existing project root:

```bash
cd /path/to/your/project
oniroute init
```

This will:
1. Detect your platform features.
2. Create `.oniroute/` subdirectories (`sessions`, `traces`, `logs`, `history`, `artifacts`).
3. Generate a project configuration at `.oniroute/config.yaml` preserving your default settings.

---

### 3. Verify Configuration & Installation

Run `oniroute doctor` and `oniroute config --validate` to verify workspace health:

```bash
# Verify system diagnostic health
oniroute doctor

# Validate configuration integrity
oniroute config --validate

# Inspect version info
oniroute version
```

---

## Configuration Compatibility

v1.0.0 configuration files (`config/default.yaml`, `config/models.yaml`, `config/policies.yaml`) are automatically merged with new v1.2 settings (`max_concurrent_missions`, `default_quality_threshold`, `telemetry_enabled`).

Missing fields are populated with safe defaults:
- `max_concurrent_missions`: `3`
- `default_quality_threshold`: `8.0`
- `telemetry_enabled`: `false`

No manual configuration editing is required.

---

## Troubleshooting Upgrade Issues

If you encounter issues during upgrade, run:

```bash
oniroute doctor
```

For detailed troubleshooting instructions, refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
