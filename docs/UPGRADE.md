# Upgrade Guide

This document outlines how to upgrade OniRoute to version 1.2.0, compatibility matrices, and rollback procedures.

## Version Compatibility Matrix

| OniRoute Version | Python Version | Config Schema Version | Status |
|---|---|---|---|
| v1.0.x | >= 3.10 | v1.0 | Deprecated |
| v1.1.x | >= 3.11 | v1.1 | Supported |
| **v1.2.x** | **>= 3.12** | **v1.2** | **Active (Current)** |

## Upgrading to v1.2.0

### Using the CLI

The easiest way to upgrade is via the built-in update command:

```bash
oniroute update
```

### Manual Upgrades

Depending on your original installation method:

**pipx:**
```bash
pipx upgrade oniroute-swarmagents
```

**pip:**
```bash
pip install --upgrade oniroute-swarmagents
```

**Homebrew:**
```bash
brew upgrade oniroute
```

**Docker:**
Pull the latest tag:
```bash
docker pull oniroute/oniroute:1.2.0
```

## Configuration Migration

Configuration files from v1.0 and v1.1 are **fully forward-compatible** with v1.2.0.
When you run `oniroute init` or any standard command, OniRoute will parse older configs seamlessly. No manual migration of `config.yaml` is required.

## Breaking Changes

There are **no breaking changes** in the v1.2.0 release. The internal architecture for swarm coordination was updated for improved efficiency, but the public CLI interface and configuration schemas remain backward-compatible.

## Rollback Procedures

If you encounter critical issues and need to revert to a previous version:

**pipx:**
```bash
pipx install oniroute-swarmagents==1.1.0 --force
```

**pip:**
```bash
pip install oniroute-swarmagents==1.1.0
```

**Homebrew:**
```bash
brew reinstall oniroute@1.1.0
```
*(Ensure you have the specific tap available).*
