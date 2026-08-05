# Configuration Reference

This document provides a comprehensive overview of OniRoute v1.2.0 configuration, detailing the hierarchy, keys, environment variable overrides, and examples.

## Configuration Hierarchy

OniRoute resolves configuration values in the following order of precedence (highest to lowest):

1. **Environment Variables**: E.g., `ONIROUTE_LOG_LEVEL=DEBUG`
2. **Project Configuration**: `.oniroute/config.yaml` (in the current directory)
3. **Global Configuration**: `~/.config/oniroute/config.yaml`
4. **Built-in Defaults**

## Global vs Project Config

- **Global Config** (`~/.config/oniroute/config.yaml`): Best for user-specific settings like default API keys, preferred LLM models, and global telemetry preferences.
- **Project Config** (`.oniroute/config.yaml`): Created via `oniroute init`. Best for project-specific settings like `review_strategy`, project workspace paths, or specific `providers`.

## Configuration Keys

Below are the primary configuration keys, their types, and descriptions:

| Key | Type | Default | Description |
|---|---|---|---|
| `version` | string | "1.2.0" | The OniRoute configuration schema version. |
| `workspace_root` | string | `.` | Root directory for the workspace. |
| `logging_level` | string | `INFO` | Standard logging levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `validation_mode` | string | `strict` | Controls config validation (`strict`, `lenient`, `off`). |
| `providers` | dict | `{}` | LLM provider configurations. |
| `mcp` | dict | `{}` | Model Context Protocol server configurations. |
| `secrets` | dict | `{}` | Explicitly defined secrets. |
| `review_strategy` | string | `standard` | Code review thoroughness (`fast`, `standard`, `deep`). |
| `healing_strategy` | string | `auto` | How agents handle errors (`auto`, `manual`, `retry`). |
| `max_concurrent_missions` | int | 5 | Maximum number of concurrent agent operations. |
| `default_quality_threshold` | float | 0.8 | Target quality score for generated artifacts (0.0 to 1.0). |
| `telemetry_enabled` | bool | false | Whether anonymous usage telemetry is sent. |

## Environment Variable Overrides

Any configuration key can be overridden using environment variables prefixed with `ONIROUTE_`.

| Config Key | Environment Variable |
|---|---|
| `logging_level` | `ONIROUTE_LOG_LEVEL` |
| `validation_mode` | `ONIROUTE_VALIDATION_MODE` |
| `review_strategy` | `ONIROUTE_REVIEW_STRATEGY` |
| `max_concurrent_missions` | `ONIROUTE_MAX_CONCURRENT` |
| `default_quality_threshold` | `ONIROUTE_QUALITY_THRESHOLD` |
| `telemetry_enabled` | `ONIROUTE_TELEMETRY` |

## Secrets Management

Never hardcode sensitive information like API keys in your `config.yaml`. Instead, reference environment variables using a `$` prefix. OniRoute resolves these at runtime.

```yaml
providers:
  openai:
    api_key: $OPENAI_API_KEY
    model: gpt-4o
```

## Examples

### Provider Configuration

```yaml
providers:
  openai:
    api_key: $OPENAI_API_KEY
    default_model: gpt-4o
  anthropic:
    api_key: $ANTHROPIC_API_KEY
    default_model: claude-3-5-sonnet-20240620
```

### MCP Configuration

```yaml
mcp:
  servers:
    local_fs:
      command: "node"
      args: ["/path/to/fs-mcp/index.js"]
    github:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: $GITHUB_PAT
```

## CLI Configuration Commands

OniRoute provides commands to manage configurations easily:

- `oniroute config`: View the fully resolved configuration.
- `oniroute config --validate`: Validates current configuration without running agents.
- `oniroute config --set key=value`: Set a specific key in the project config.

Example:
```bash
oniroute config --set logging_level=DEBUG
```
