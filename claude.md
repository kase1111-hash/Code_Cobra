# Code Cobra - Claude Guide

## Project Overview

Code Cobra is a multi-agent AI coding system for autonomous code generation and security hardening. It transforms prose-first specifications into production-ready code through a three-stage LLM ensemble pipeline running locally via Ollama.

**Version:** 1.0.2

## Architecture

### Three-Stage Pipeline

```
Input Spec → Step Parser → [For Each Step]:
    ├─ Model A (Creative): draft generation (temp 0.8)
    ├─ Model B (Analytical): error correction (temp 0.3, iterative)
    └─ Model C (Adversarial): security hardening (temp 0.7, iterative)
→ OutputScanner → AuditLogger → final_output.txt
```

### Key Classes

- **Config**: System configuration with JSON/env/CLI override support
- **GuideLoader**: Parses step-by-step guide files with regex validation
- **OllamaClient**: HTTP client with 3-attempt retry logic and exponential backoff
- **ModelPipeline**: Three-stage orchestration (creative → analytical → adversarial)
- **WorkflowEngine**: Main workflow coordinator with checkpointing and audit logging
- **GuideChain**: Sequential multi-guide execution with accumulated context
- **OutputScanner**: Scans model output for secrets before writing to disk
- **AuditLogger**: Append-only JSON-lines structured audit log
- **Checkpoint**: Save/restore workflow state with HMAC-SHA256 integrity

### Security Helpers

- `_validate_path_within_base()`: Canonicalizes paths and rejects traversal outside working directory
- `_check_for_injection()`: Heuristic prompt injection detection in spec content
- `OutputScanner.scan()`: Detects API keys, tokens, and private key blocks in output

## Tech Stack

- **Python 3.8+** (supports 3.8, 3.9, 3.10, 3.11, 3.12)
- **Ollama API** (localhost:11434) - Local LLM inference
- **Docker/Docker Compose** - Container deployment

## Project Structure

```
Code_Cobra/
├── autonomous_ensemble.py    # Main application (~1000 lines)
├── config/                   # Environment configs (dev/stage/prod)
├── scripts/                  # Setup, security scanning
│   ├── setup.sh
│   └── backdoor_check.py
├── tests/                    # Test suite (151 tests)
├── guides/                   # Example workflow guides
├── docs/                     # Documentation
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   └── FAQ.md
├── coding_guide.txt          # 40-step code generation workflow
└── post_coding_guide.txt     # 40-step security hardening workflow
```

## Development Commands

```bash
make install          # Production dependencies
make install-dev      # Include dev dependencies
make lint             # Run flake8
make typecheck        # Run mypy
make security         # Run bandit security scan
make test             # Run unittest suite
make dry-run          # Validate guides without models
make all              # install → lint → typecheck → test
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

# Guide chaining
python autonomous_ensemble.py --spec "..." --chain coding_guide.txt post_coding_guide.txt
```

## Configuration

Configuration is loaded in order (later overrides earlier):
1. Built-in defaults
2. `Config.from_json()` - JSON config files
3. `Config.from_env()` - Environment variables / .env file
4. CLI arguments

Key environment variables:
- `OLLAMA_API` - Ollama endpoint (default: http://localhost:11434/api/generate)
- `MODEL_A/B/C` - Model names for each pipeline stage
- `TEMP_CREATIVE/ANALYTICAL/ADVERSARIAL` - Temperature settings
- `MAX_TOKENS` - Token limit (default: 2000)
- `MAX_ITERATIONS` - Correction iterations (default: 3)
- `CHECKPOINT_SECRET` - HMAC key for checkpoint integrity (default: "code-cobra-local")

## Testing

Test modules in `tests/` (151 tests total):
- `test_core.py` - Config, StepContext, GuideLoader, StateManager
- `test_acceptance.py` - Full workflow scenarios
- `test_integration.py` - Multi-component interactions
- `test_security.py` - Security validations (path traversal, HMAC, injection detection, output scanning)
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
- **ValueError**: Config/Checkpoint validates structure; path validation rejects traversal
- **ConnectionError/TimeoutError**: OllamaClient retries 3x with exponential backoff
- **HTTPError**: Retry on 5xx, fail immediately on 4xx

## Important Notes

- Ollama must be running locally with required models pulled
- Guide files use "Step N: description" format (regex validated)
- Checkpoints are HMAC-verified on load to detect tampering
- Prompts use XML delimiter tags to separate instructions from user data
- Model output is scanned for secrets before writing to disk
- All file paths are canonicalized and boundary-checked
