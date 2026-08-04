# OniRoute v1.0.0

## Highlights

OniRoute is a local-first, provider-independent engineering organization framework with a frozen v0.6 runtime and a complete public documentation and contribution surface. Version 1.0.0 is licensed under Apache-2.0.

## Major capabilities

- Agent, Skill, Workflow, Knowledge, Package, Tool, and model metadata catalogs.
- Repository loading, validation, graph resolution, immutable Context, deterministic Workflow planning/execution, events, history, and artifacts.
- Universal Model, Invocation, Tool/MCP, and Governance layers.
- Local Dry Run, mock-verifiable AI invocation, approvals, permissions, budgets, risk, and audit records.
- Typer/Rich CLI for discovery, planning, execution, inspection, selection, governance, and diagnostics.

## Supported platforms and protocols

Python 3.12+ on platforms supported by the Python standard library. Reference invocation adapters support Ollama and OpenAI-compatible HTTP endpoints. Metadata catalogs describe additional providers/protocols without claiming SDK support.

## Supported providers and local models

Provider metadata includes OpenAI, Anthropic, Google, OpenRouter, Groq, Together, Fireworks, Cohere, Mistral, DeepSeek, Hugging Face, Ollama, LM Studio, vLLM, LocalAI, llama.cpp, MLX, KoboldCpp, TGI, and Custom. Ollama and OpenAI-compatible local servers are first-class reference paths.

## Known limitations

Tool/MCP execution is not implemented; most state is process-local; streaming adapters currently yield one completed chunk; unknown-license and copyleft Community sources remain excluded or reference-only.

## Upgrade notes

Install with Python 3.12+ and `python -m pip install -e .`. Review `config/models.yaml` and `config/policies.yaml`; default AI approval remains Dry Run. Run `oniroute doctor` and `python -m pytest -q` after installation.
