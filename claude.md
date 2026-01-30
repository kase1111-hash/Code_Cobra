# Code Cobra - Claude Guide

## Project Overview

Code Cobra is a multi-agent AI coding system for autonomous code generation and security hardening. It transforms prose-first specifications into production-ready code through a three-stage LLM ensemble pipeline running locally via Ollama.

**Version:** 1.0.0 (Production-Ready)

## Architecture

### Three-Stage Pipeline

```
Input Spec → Step Parser → [For Each Step]:
    ├─ Model A (Creative): draft generation (temp 0.8)
    ├─ Model B (Analytical): error correction (temp 0.3, iterative)
    └─ Model C (Adversarial): security hardening (temp 0.7, iterative)
→ Accumulator → final_output.txt
```

### Core Modules

| File | Purpose |
|------|---------|
| `autonomous_ensemble.py` | Main application - orchestrates the 3-stage pipeline |
| `logging_config.py` | Structured JSON logging for ELK/CloudWatch |
| `monitoring.py` | Health checks and system monitoring |
| `telemetry.py` | Metrics collection and performance tracking |

### Key Classes

- **Config**: System configuration with JSON/env/CLI override support
- **GuideLoader**: Parses step-by-step guide files with regex validation
- **OllamaClient**: HTTP client with 3-attempt retry logic and exponential backoff
- **ModelPipeline**: Three-stage orchestration (creative → analytical → adversarial)
- **WorkflowEngine**: Main workflow coordinator with checkpointing
- **GuideChain**: Sequential multi-guide execution with accumulated context

## Tech Stack

- **Python 3.8+** (supports 3.8, 3.9, 3.10, 3.11, 3.12)
- **Ollama API** (localhost:11434) - Local LLM inference
- **Docker/Docker Compose** - Container deployment

## Project Structure

```
Code_Cobra/
├── autonomous_ensemble.py    # Main application
├── logging_config.py         # Structured logging
├── monitoring.py             # Health checks
├── telemetry.py              # Metrics collection
├── config/                   # Environment configs (dev/stage/prod)
├── scripts/                  # Setup, deploy, rollback scripts
├── tests/                    # Test suite (125+ tests)
├── docs/                     # Extended documentation
├── coding_guide.txt          # 40-step code generation workflow
└── post_coding_guide.txt     # 40-step security hardening workflow
```

## Development Commands

```bash
# Install dependencies
make install          # Production dependencies
make install-dev      # Include dev dependencies

# Code quality
make lint             # Run flake8 (100 char line limit)
make typecheck        # Run mypy (strict mode)
make security         # Run bandit security scan
make analyze          # All static analysis

# Testing
make test             # Run unittest suite
make dry-run          # Validate guides without models

# Build
make all              # install → lint → typecheck → test
make clean            # Remove caches and output files
```

## Running the Application

```bash
# Basic execution
python autonomous_ensemble.py --spec "Build a REST API" --guide coding_guide.txt

# Dry-run validation (no models)
python autonomous_ensemble.py --dry-run --guide coding_guide.txt

# With checkpointing
python autonomous_ensemble.py --spec "..." --checkpoint progress.json
python autonomous_ensemble.py --spec "..." --resume progress.json

# Guide chaining (coding then security)
python autonomous_ensemble.py --spec "..." --chain coding_guide.txt post_coding_guide.txt
```

## Configuration

Configuration is loaded in order (later overrides earlier):
1. Built-in defaults
2. `Config.from_json()` - JSON config files
3. `Config.from_env()` - Environment variables / .env file
4. CLI arguments

Environment configs in `config/`:
- `dev.json` - Development (verbose, qwen models)
- `stage.json` - Staging
- `prod.json` - Production

Key environment variables:
- `OLLAMA_API` - Ollama endpoint (default: http://localhost:11434/api/generate)
- `MODEL_A/B/C` - Model names for each pipeline stage
- `TEMP_CREATIVE/ANALYTICAL/ADVERSARIAL` - Temperature settings
- `MAX_TOKENS` - Token limit (default: 2000)
- `MAX_ITERATIONS` - Correction iterations (default: 3)

## Testing

Test modules in `tests/`:
- `test_core.py` - Config, StepContext, GuideLoader, StateManager
- `test_acceptance.py` - Full workflow scenarios
- `test_integration.py` - Multi-component interactions
- `test_security.py` - Security validations
- `test_dynamic.py` - Dynamic behavior, edge cases
- `test_exploits.py` - Vulnerability/attack scenarios
- `test_performance.py` - Benchmarks, scalability
- `run_regression.py` - Regression detection

## Code Conventions

- **Line limit**: 100 characters (E501 ignored)
- **Type hints**: Required (mypy strict mode)
- **Docstrings**: Google style
- **Imports**: stdlib → third-party → local

## Error Handling

- **FileNotFoundError**: GuideLoader lists available guides
- **ValueError**: Config/Checkpoint validates structure
- **ConnectionError/TimeoutError**: OllamaClient retries 3x with exponential backoff
- **HTTPError**: Retry on 5xx, fail immediately on 4xx

## Extension Points

1. **Custom Hooks**: `post_draft`, `post_correction`, `post_security` callbacks via `PipelineHooks`
2. **Guide Chaining**: Sequential multi-guide workflows with context accumulation
3. **Checkpoint System**: Resume from any completed step
4. **Monitoring**: Health checks via `HealthChecker`, metrics via `MetricsCollector`

## Docker

```bash
# Build and run with Ollama
docker-compose up

# Build image
docker build -t code-cobra .

# Run container
docker run -e OLLAMA_API=http://ollama:11434/api/generate code-cobra --spec "..." --guide coding_guide.txt
```

## Important Notes

- Ollama must be running locally with required models pulled
- Guide files use "Step N: description" format (regex validated)
- Checkpoints enable resumable workflows after interruption
- Model A uses high temperature (0.8) for creativity
- Models B/C iterate up to 3x and stop on convergence
