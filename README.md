<p align="center">
  <img src="docs/images/oniroute-banner.png" alt="OniRoute Swarm Agents banner" width="100%">
</p>

<h1 align="center">OniRoute Swarm Agents</h1>

<p align="center"><strong>Organization Level Swarm Coding AI Agents — Local-First, Provider-Independent Swarm AI Architecture & Runtime.</strong></p>

<p align="center">
  <a href="LICENSE"><img alt="License Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-2f6f9f.svg"></a>
  <a href="pyproject.toml"><img alt="Python 3.12 or newer" src="https://img.shields.io/badge/python-3.12%2B-3776ab.svg"></a>
  <a href="VERSION"><img alt="Version 1.2.0" src="https://img.shields.io/badge/version-1.2.0-29a89a.svg"></a>
  <a href="docs/ONIROUTE_CERTIFICATION_REPORT.md"><img alt="Coverage 100%" src="https://img.shields.io/badge/coverage-100%25-green.svg"></a>
  <a href="docs/RUNTIME_ARCHITECTURE.md"><img alt="Runtime v0.6" src="https://img.shields.io/badge/runtime-v0.6-244f73.svg"></a>
  <a href="docs/INSTALL.md"><img alt="Documentation Complete" src="https://img.shields.io/badge/docs-complete-0f766e.svg"></a>
  <img alt="Open Source" src="https://img.shields.io/badge/open%20source-yes-2e8b57.svg">
  <a href="docs/CLI_REFERENCE.md"><img alt="CLI" src="https://img.shields.io/badge/interface-CLI-444.svg"></a>
  <img alt="Provider Agnostic" src="https://img.shields.io/badge/provider-agnostic-7b61a8.svg">
  <img alt="Model Agnostic" src="https://img.shields.io/badge/model-agnostic-8b6f47.svg">
</p>

<p align="center">
  <a href="https://github.com/AniruddhaDas1/OniRoute_SwarmAgents/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/AniruddhaDas1/OniRoute_SwarmAgents?style=social"></a>
  <a href="https://github.com/AniruddhaDas1/OniRoute_SwarmAgents/forks"><img alt="GitHub Forks" src="https://img.shields.io/github/forks/AniruddhaDas1/OniRoute_SwarmAgents?style=social"></a>
  <a href="https://github.com/AniruddhaDas1/OniRoute_SwarmAgents/issues"><img alt="GitHub Issues" src="https://img.shields.io/github/issues/AniruddhaDas1/OniRoute_SwarmAgents"></a>
  <a href="https://github.com/AniruddhaDas1/OniRoute_SwarmAgents/commits/main"><img alt="GitHub Last Commit" src="https://img.shields.io/github/last-commit/AniruddhaDas1/OniRoute_SwarmAgents"></a>
</p>

---

## Project Overview

OniRoute is an architecture-first, local-first framework for modeling, operating, and orchestrating governed engineering organizations composed of specialized AI Agents, reusable Skills, declarative Workflows, Knowledge Sources, Universal Model Abstractions (UMAL), and local runtime engines.

Version **1.2.0 ("Swarm Intelligence")** certifies the complete Product Layer (P1–P6), adding zero-setup multi-platform distribution (`pipx`, `pip`, Homebrew, Docker, Standalone Executables), interactive natural language routing, hierarchical configuration, and automated release engineering.

---

## Architecture Diagram

The runtime routes declarative work through explicit transformation, optimization, and governance boundaries:

```mermaid
flowchart TD
    NL[Natural Language / Prompt] --> NLR[Natural Language Router]
    NLR --> MC[Mission Control Engine]
    MC --> PB[Project Blueprint Engine]
    PB --> SA[Swarm Allocation Engine]
    SA --> EW[Engineering Worker Engine]
    EW --> QG[Quality Gate Engine]
    QG --> SH[Self-Healing Engine]
    SH --> VA[Verification & Acceptance]
    
    subgraph Execution & Governance Layer
        UMAL[Universal Model Abstraction]
        ICOE[Intelligent Context Optimization]
        GOV[Governance & Policy Engine]
    end
    
    EW -. model inference .-> UMAL
    PB -. context optimization .-> ICOE
    EW -. security & budget .-> GOV
```

---

## Supported Platforms

| Platform | Support | Distribution Vehicle |
| :--- | :--- | :--- |
| **macOS** (12+, `arm64`, `x86_64`) | Fully Supported | Homebrew, `pipx`, `pip`, Standalone Executable |
| **Linux** (Ubuntu 22.04+, Debian 12+, Fedora, Arch) | Fully Supported | Docker, `pipx`, `pip`, Standalone Executable |
| **Windows** (10/11 `x86_64`, WSL2) | Fully Supported | `pipx`, `pip`, Standalone `.exe` Executable |
| **Python Runtimes** | Python >= 3.12 (3.12, 3.13, 3.14) | PyPI Wheel & Source Distribution |

---

## Installation

Choose your preferred installation method:

### 1. pipx (Recommended for CLI)
```bash
pipx install oniroute-swarmagents
```

### 2. Standard pip
```bash
pip install oniroute-swarmagents
```

### 3. Homebrew (macOS / Linux)
```bash
brew install oniroute/tap/oniroute
```

### 4. Docker Container
```bash
docker run --rm -v $(pwd):/workspace oniroute/oniroute:1.2.0 build "my app"
```

### 5. Automated Install Script
```bash
curl -fsSL https://raw.githubusercontent.com/AniruddhaDas1/OniRoute_SwarmAgents/main/scripts/install.sh | bash
```

See [docs/INSTALL.md](docs/INSTALL.md) for full installation details.

---

## Quick Start

Get started with OniRoute in 3 simple commands:

```bash
# 1. Initialize your workspace (detects platform, Git, Docker, and MCP)
oniroute init

# 2. Run system diagnostics
oniroute doctor

# 3. Build a project using Natural Language
oniroute build "Create a modern real estate web application with Next.js and Tailwind"
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a detailed walkthrough.

---

## Mission Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Router as NL Router
    participant Mission as Mission Control
    participant Swarm as Swarm Engine
    participant Worker as Engineering Worker
    participant Quality as Quality Gate

    User->>Router: "oniroute build 'real estate app'"
    Router->>Mission: Intake Prompt & Resolve Intent
    Mission->>Swarm: Blueprint Project & Allocate Agents
    Swarm->>Worker: Dispatch Engineering Contracts
    Worker->>Quality: Run Verification & Quality Gates
    Quality-->>User: Present Engineering Results & Artifacts
```

---

## Examples

### 1. Natural Language Project Creation
```bash
oniroute build "A high-performance REST API in FastAPI with PostgreSQL and JWT auth"
```

### 2. Workspace Diagnostics & Storage Inspection
```bash
oniroute workspace
```

### 3. Configuration Management
```bash
# View configuration
oniroute config

# Set log level
oniroute config logging_level --set DEBUG

# Validate configuration
oniroute config --validate
```

---

## CLI Commands Summary

OniRoute features 59 registered CLI commands in `cli/main.py`:

| Category | Primary Commands |
| :--- | :--- |
| **Distribution** | `init`, `doctor`, `config`, `update`, `version` |
| **Natural Language** | `build`, `create`, `fix`, `refactor`, `migrate` |
| **Discovery** | `workspace`, `list`, `inspect`, `search`, `skills`, `rank-skills` |
| **Orchestration** | `execute`, `run`, `plan`, `coordinate`, `mission`, `deployment` |
| **Engineering** | `scaffold`, `blueprint-project`, `allocate`, `contracts`, `engineer`, `heal` |
| **Governance** | `policy`, `audit`, `approvals`, `permissions`, `budget` |

See [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for complete CLI documentation.

---

## Configuration

OniRoute uses a 3-tier configuration hierarchy (Environment Overrides > Project Config > Global Config):

- **Global Config**: `~/.config/oniroute/config.yaml`
- **Project Config**: `.oniroute/config.yaml`
- **Environment Overrides**:
  - `ONIROUTE_LOG_LEVEL`: `DEBUG | INFO | WARNING | ERROR`
  - `ONIROUTE_MAX_CONCURRENT`: Max concurrent missions (e.g. `3`)
  - `ONIROUTE_QUALITY_THRESHOLD`: Quality threshold (0–10, default `8.0`)
  - `ONIROUTE_TELEMETRY`: `true | false`

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for full configuration specifications.

---

## Repository Statistics

- **Python Core & Runtime**: 309 files (43,672 LOC)
- **Documentation Suite**: 6,689 Markdown files (90,293 Lines)
- **Declarative YAML Contracts**: 1,436 schema files
- **Automated Tests**: 671 test cases (100% pass rate)

---

## Roadmap

- [x] **v1.0.0 — Core Engine Frozen**: Runtime v0.6, ICOE v1.1, UMAL, Governance.
- [x] **v1.2.0 — Product Layer Frozen**: Zero-setup distribution (`pipx`, `brew`, `docker`), `init`, `config`, `doctor`, `update`, `version`, NL Router.
- [ ] **v1.3.0 — Distributed Swarm Mesh**: Multi-node remote agent coordination over gRPC/WebSocket.

---

## Contributing

We welcome community contributions! Please read [CONTRIBUTING.md](docs/CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) before submitting pull requests.

---

## License

OniRoute is released under the **Apache-2.0 License**. See [LICENSE](LICENSE) for details.
