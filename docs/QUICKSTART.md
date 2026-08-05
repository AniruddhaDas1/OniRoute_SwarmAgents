# Quickstart Guide

Get up and running with OniRoute v1.2.0 in under 5 minutes. This guide will walk you through installation, initialization, and running your first natural language project build.

## 1. Install OniRoute

The quickest way to install OniRoute is using `pipx`, ensuring an isolated environment.

```bash
pipx install oniroute-swarmagents
```

*(For other installation methods, refer to the [Installation Guide](./INSTALL.md).)*

## 2. Initialize the Workspace

Navigate to an empty directory or your project root and initialize OniRoute:

```bash
cd my-project
oniroute init
```

This command creates a `.oniroute/` directory containing default configuration, logs, traces, and artifact directories.

## 3. Verify Your Setup

Ensure your workspace and installation are functioning correctly by running the diagnostic tool:

```bash
oniroute doctor
```

This will check for dependencies, Python version, valid configurations, and workspace integrity.

## 4. Configure Your Project (Optional)

By default, OniRoute uses sensible defaults. To view or adjust your configuration (such as setting up LLM provider API keys):

```bash
oniroute config
```

You can set values directly:
```bash
oniroute config --set providers.openai.api_key "$OPENAI_API_KEY"
```

*See [Configuration Guide](./CONFIGURATION.md) for full details.*

## 5. Your First Build

You are now ready to orchestrate AI swarm agents! Let's ask OniRoute to build something.

```bash
oniroute build "a personal portfolio website"
```

OniRoute will automatically formulate a plan, spawn specialized agents, write the code, and save the artifacts in your workspace.

## What's Next?

- ⚙️ Deep dive into setup: [Configuration Reference](./CONFIGURATION.md)
- 🚀 Advanced Usage: Check out `oniroute plan` and `oniroute mission`.
- 🔍 Troubleshooting: Hit a snag? See [Troubleshooting](./TROUBLESHOOTING.md).
