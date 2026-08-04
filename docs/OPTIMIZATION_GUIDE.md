# Optimization Guide

ICOE v1.1 is the optional layer between Context and UMAL. The governed execution path is `Workflow → Execution → Context → ICOE → UMAL → Invocation → Model`. Configuration in `config/models.yaml` selects Enabled, Disabled, or Dry Run mode and declares protected context, artifacts, prompts, and Skills. `--no-optimization` explicitly bypasses optimization for a Workflow run.

Native modules cover Context, Prompt, Repository, Skill, Artifact, Terminal, and Conversation inputs. Each deterministic transformation emits measurements and an explainable report. The native plugin is mandatory infrastructure; RTK, Tree-sitter AST, and repository-graph integrations remain optional metadata and cannot prevent native operation.

Use `oniroute optimize explain` for effective policy and `oniroute optimize report` for in-memory execution records.
