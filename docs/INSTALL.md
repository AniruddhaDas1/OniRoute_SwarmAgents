# Installation Guide

Welcome to the comprehensive installation guide for OniRoute v1.2.0. This document covers all supported installation methods, prerequisites, verification steps, and uninstallation procedures.

## Prerequisites

Before installing OniRoute, ensure your system meets the following requirements:
- **Python**: version >= 3.12
- **Git**: version >= 2.30

## Installation Methods

### 1. Installation via pipx (Recommended)

`pipx` is the recommended way to install Python CLI applications as it installs them in isolated environments.

```bash
pipx install oniroute-swarmagents
```

### 2. Installation via pip

You can install OniRoute globally or in a virtual environment using standard `pip`.

```bash
pip install oniroute-swarmagents
```

### 3. Installation via Homebrew (macOS/Linux)

For users on macOS or Linux using Homebrew:

```bash
brew install oniroute/tap/oniroute
```

### 4. Installation via Docker

If you prefer containerized environments, OniRoute is available via Docker. This method requires mounting your workspace directory.

```bash
docker run --rm -v $(pwd):/workspace oniroute/oniroute:1.2.0
```

### 5. Standalone Executables from GitHub Releases

You can download pre-compiled standalone executables for your platform from the [GitHub Releases](https://github.com/AniruddhaDas1/OniRoute_SwarmAgents/releases) page. No Python installation is required for this method.

1. Download the executable for your OS (e.g., `oniroute-macos`, `oniroute-linux`, `oniroute-windows.exe`).
2. Make it executable (macOS/Linux): `chmod +x oniroute-macos`
3. Move it to a directory in your PATH.

### 6. Building from Source

For contributors and developers:

```bash
git clone https://github.com/AniruddhaDas1/OniRoute_SwarmAgents.git
cd OniRoute_SwarmAgents
pip install -e .
```

## Verification

After installation, verify that OniRoute is correctly installed:

```bash
oniroute version
```
This should display version 1.2.0 and platform info.

Run the built-in diagnostic tool to validate your installation and workspace:
```bash
oniroute doctor
```

## Uninstallation

Depending on your installation method, use one of the following commands:

- **pipx**: `pipx uninstall oniroute-swarmagents`
- **pip**: `pip uninstall oniroute-swarmagents`
- **Homebrew**: `brew uninstall oniroute`
- **Docker**: `docker rmi oniroute/oniroute:1.2.0`
- **Executable**: Delete the downloaded binary.

## Platform-Specific Notes

### macOS
- If you encounter Gatekeeper issues with standalone executables, you may need to allow the app in System Settings > Privacy & Security, or run `xattr -d com.apple.quarantine oniroute`.

### Linux
- Ensure you have the necessary permissions if installing via `pip` globally (consider using `sudo` or `--user`). `pipx` avoids this issue.

### Windows
- Ensure the installation directory is added to your system's PATH. If using Docker, ensure path formats for volume mounts are correct (e.g., `-v %cd%:/workspace`).
