# OniRoute SwarmAgents

OniRoute is a local-first, provider-independent framework for modeling and operating an engineering organization of specialized AI Agents, reusable Skills, declarative Workflows, Knowledge Sources, Packages, Tools, and model providers.

The repository includes frozen architecture through Phase 5 and the frozen v0.6 Python runtime. It can discover and validate repository metadata, resolve relationships, build Context, plan and run Workflows, select models and tools, invoke OpenAI-compatible or Ollama endpoints, and enforce local governance.

## Key features

- 296 Agent and Sub-Agent definitions, 1,087 Skills, and 20 Official Workflows.
- Local repository loader, registry, validation, resolution graph, and Context Engine.
- Deterministic Workflow planning, execution history, events, and artifacts.
- Universal model, invocation, Tool/MCP, and governance abstractions.
- OpenAI-compatible and Ollama reference adapters with local models as first-class citizens.
- No telemetry, database, SaaS dependency, or mandatory internet access.

## Architecture

```text
CLI / Workflow Engine
        |
Resolution -> Context -> Execution Plan
        |                    |
       UMAL            Governance Policy
        |                /          \
Invocation Adapters   AI Requests   Tool Metadata
        |
Configured local or remote model endpoint
```

See [Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md) and [Runtime Architecture](docs/RUNTIME_ARCHITECTURE.md).

## Repository structure

| Path | Purpose |
|---|---|
| `agents/` | Organizational Agent and Sub-Agent definitions |
| `skills/` | Official and community Skill catalog |
| `workflows/` | Workflow specification, registry, resolution, and Official library |
| `knowledge/`, `packages/`, `mappings/` | Knowledge, packaging, and relationship metadata |
| `runtime/` | Frozen v0.6 local Python runtime |
| `cli/` | Typer command-line interface |
| `config/` | Runtime, model, tool, and governance configuration |
| `examples/`, `templates/` | Learning examples and contribution starters |
| `docs/` | Architecture, operations, contribution, and release guidance |

## Installation

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
oniroute doctor
```

See [Installation](docs/INSTALLATION.md) for platform notes.

## Quick start

```bash
oniroute list workflows
oniroute inspect workflow rest-api-design
oniroute plan workflow rest-api-design
oniroute run workflow rest-api-design
oniroute explain workflow rest-api-design
oniroute recommend-model --capability reasoning --local
oniroute recommend-tool --capability database
oniroute policy workflow rest-api-design
```

The default AI approval policy is Dry Run. Configure endpoints and governance explicitly before enabling Automatic invocation.

## Providers, local models, and protocols

The metadata catalog supports OpenAI, Anthropic, Google, OpenRouter, Groq, Together, Fireworks, Cohere, Mistral, DeepSeek, Hugging Face, Ollama, LM Studio, vLLM, LocalAI, llama.cpp, MLX, KoboldCpp, TGI, and Custom providers. Reference invocation adapters implement OpenAI-compatible and Ollama protocols. Other provider/protocol records are extension points, not claims of implemented SDK support.

Supported protocol metadata includes OpenAI-compatible, Anthropic, Gemini, Ollama, MCP, HTTP, Python, CLI, Local Process, and Custom.

## Core concepts

- **Agent:** accountable organizational responsibility.
- **Skill:** reusable bounded capability.
- **Workflow:** declarative Agent collaboration contract.
- **Context:** immutable structured information routed between boundaries.
- **Model:** provider-independent capability metadata selected through UMAL.
- **Tool:** governed local or MCP capability metadata.
- **Governance:** mandatory policy, approval, budget, risk, and audit checks.

## Roadmap

Phases 1–6 are frozen. Phase 7 prepares public distribution and community operations. Future changes to frozen layers require an approved phase or Architecture Change Request.

## Contributing

Read [Contributing](docs/CONTRIBUTING.md), the [Developer Guide](docs/DEVELOPER_GUIDE.md), and [Code of Conduct](.github/CODE_OF_CONDUCT.md). Use the provided templates and keep changes small, provider-independent, validated, and within frozen-boundary rules.

## License and acknowledgements

Released under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE), [AUTHORS](AUTHORS), and [Third-Party Notices](docs/THIRD_PARTY_NOTICES.md). Community Skill sources retain their recorded provenance and licensing metadata.

Thanks to the open-source Python ecosystem, community Skill authors, and contributors whose attributed work is represented in the repository.
