# AICodeGenCrew

AICodeGenCrew is a fully local, on-premises AI-powered toolkit for end-to-end Software Development Lifecycle (SDLC) automation. It analyzes existing repositories, generates evidence-based architecture documentation, and supports the full development workflow from planning to deployment.

## Key Features

- **Fully Automated Architecture Discovery**: Extracts deterministic facts from codebases and synthesizes C4 diagrams and arc42 documentation.
- **Evidence-Based**: Every claim in generated documentation is traceable to source code evidence.
- **On-Premises Operation**: Runs entirely on your infrastructure with local LLMs - no data leaves your network.
- **Scalable**: Handles repositories from small projects to enterprise-scale systems.
- **Standards-Compliant**: Outputs follow C4 model and arc42 documentation standards.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Phases](#phases)
- [Configuration](#configuration)
- [Usage](#usage)
- [Outputs](#outputs)
- [Contributing](#contributing)
- [License](#license)
- [Documentation](#documentation)

## Installation

### Prerequisites

- Python 3.10+
- Local LLM runtime (e.g., Ollama) for synthesis phases

### Setup

1. Clone the repository:
   ```bash
   git clone <repo-url> aicodegencrew
   cd aicodegencrew
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   ```

   Edit `.env`:
   ```env
   PROJECT_PATH=/path/to/your/repo
   LLM_PROVIDER=local
   MODEL=all-minilm:latest
   INDEX_MODE=auto
   ```

3. Install dependencies and prepare runtimes as needed.

## Quick Start

Run the complete architecture workflow:
```bash
python -m aicodegencrew run --preset architecture_workflow
```

Run only deterministic phases (no LLM required):
```bash
python -m aicodegencrew run --preset facts_only
```

## Phases

The SDLC pipeline consists of 8 phases:

| Phase | Name | Type | Description | Status |
|-------|------|------|-------------|--------|
| 0 | Indexing | Pipeline | Vector indexing of repository content | Implemented |
| 1 | Architecture Facts | Pipeline | Deterministic extraction of facts and evidence | Implemented |
| 2 | Architecture Synthesis | Crew | AI generation of C4 and arc42 documentation | Implemented |
| 3 | Review | Crew | Consistency checks and quality validation | Planned |
| 4 | Development | Crew | Backlog generation and planning | Planned |
| 5 | Code Generation | Crew | Feature implementation and refactoring | Planned |
| 6 | Testing | Crew | Test generation and coverage | Planned |
| 7 | Deployment | Pipeline | CI/CD integration and releases | Planned |

**Core Principles:**
- **Evidence-First**: All outputs must reference code evidence.
- **Deterministic Discovery**: Facts are extracted without LLMs.
- **Phase Isolation**: Clear inputs/outputs per phase.
- **Incremental Adoption**: Phases can run independently.

## Configuration

Key environment variables:

- `PROJECT_PATH`: Path to repository to analyze
- `LLM_PROVIDER`: `local` or `onprem`
- `MODEL`: LLM/embedding model identifier
- `INDEX_MODE`: `off`, `auto`, `force`, `smart`

See `phases_config.yaml` for additional settings.

## Usage

### CLI Commands

```bash
python -m aicodegencrew <command> [options]
```

### Examples

- List phases and presets:
  ```bash
  python -m aicodegencrew list
  ```

- Run full workflow:
  ```bash
  python -m aicodegencrew run --preset architecture_workflow
  ```

- Run specific phases:
  ```bash
  python -m aicodegencrew run --phases phase0_indexing phase1_architecture_facts
  ```

- Index only:
  ```bash
  python -m aicodegencrew index --force
  ```

## Outputs

Generated artifacts are saved to `knowledge/architecture/`:

- `architecture_facts.json`: Canonical architecture facts
- `evidence_map.json`: Evidence traceability mapping
- `c4/`: C4 diagrams (Markdown + Draw.io)
- `arc42/`: Complete arc42 documentation (12 chapters)

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Run tests and linters.
4. Submit a pull request.

See `tests/` for test suite and `config/phases_config.yaml` for configuration.

## License

Proprietary. See [LICENSE](LICENSE) for details.

## Documentation

- [AI SDLC Architecture](docs/AI_SDLC_ARCHITECTURE.md)
- Diagrams: `docs/diagrams/`