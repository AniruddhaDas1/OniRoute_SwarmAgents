# Troubleshooting Guide

This guide helps diagnose and resolve common issues encountered when installing, configuring, or running OniRoute.

## Diagnostic Commands

If you encounter unexpected behavior, your first step should be running our built-in diagnostic tools:

```bash
# Validates installation, dependencies, and workspace health
oniroute doctor

# Check version and platform info
oniroute version --json

# Verify configuration syntax and schema
oniroute config --validate
```

## Installation Issues

### Python Version Errors
**Error:** `Requires-Python >= 3.12`
**Solution:** Ensure you are using Python 3.12 or newer. Check with `python --version`. Use tools like `pyenv` or `conda` to manage Python versions if needed.

### Permission Errors (pip)
**Error:** `Permission denied: '/usr/local/lib/python3.x/site-packages'`
**Solution:** Do not use `sudo pip`. Instead, use `pipx install oniroute-swarmagents`, or use `pip install --user oniroute-swarmagents`.

## Initialization Issues

### Workspace Creation Fails
**Error:** `Failed to create .oniroute/ directory`
**Solution:** Ensure you have write permissions in your current directory. Check folder ownership and permissions.

## Configuration Issues

### Validation Errors
**Error:** `Invalid configuration: 'logging_level' expected one of [DEBUG, INFO, WARNING, ERROR]`
**Solution:** Check your `config.yaml` for typos. Run `oniroute config --validate` to catch schema violations early.

### Secrets Not Resolving
**Error:** `Missing API key for provider: openai`
**Solution:** Ensure your environment variable is exported correctly in your shell profile.
```bash
export OPENAI_API_KEY="your-key"
```
Also ensure your `config.yaml` references it as `$OPENAI_API_KEY`.

## Platform-Specific Issues

### macOS Gatekeeper
**Issue:** "oniroute cannot be opened because the developer cannot be verified."
**Solution:** Run the following command on the executable:
```bash
xattr -d com.apple.quarantine /path/to/oniroute
```
Alternatively, allow it manually in System Settings > Privacy & Security.

### Linux Permissions
**Issue:** Cannot execute binary after download.
**Solution:** Make sure you set the execute permission: `chmod +x oniroute-linux`

### Windows Paths
**Issue:** File paths not resolving in configurations.
**Solution:** Ensure paths use forward slashes (`/`) or escaped backslashes (`\\`) in your YAML config.

## Docker Issues

### Volume Mounting Fails
**Issue:** The agents cannot read or write to your project directory.
**Solution:** Ensure you are mounting the volume correctly.
- Linux/macOS: `-v $(pwd):/workspace`
- Windows CMD: `-v %cd%:/workspace`
- Windows PowerShell: `-v ${PWD}:/workspace`

## MCP Server Issues

### Server Detection Fails
**Issue:** `Failed to spawn MCP server: node`
**Solution:** Ensure the runtime required for the MCP server (e.g., `node`, `npx`, `python`) is installed and available in your system's PATH. Ensure paths to local MCP scripts in `config.yaml` are absolute or correctly relative to `workspace_root`.

## Getting Help

If these steps do not resolve your issue:
- Check our [GitHub Discussions](https://github.com/AniruddhaDas1/OniRoute_SwarmAgents/discussions).
- Search or open an issue on [GitHub Issues](https://github.com/AniruddhaDas1/OniRoute_SwarmAgents/issues).
