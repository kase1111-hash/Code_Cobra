# Code Cobra API Reference

## Overview

Code Cobra provides both a CLI interface and a Python API for programmatic use.

---

## CLI Reference

### Basic Usage

```bash
python autonomous_ensemble.py [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--spec` | string | Required* | Project specification (string or file path) |
| `--guide` | string | `coding_guide.txt` | Path to guide file |
| `--output` | string | `final_output.txt` | Output file path |
| `--config` | string | None | JSON config file path |
| `--verbose` | flag | False | Enable detailed logging |
| `--dry-run` | flag | False | Validate without running models |
| `--checkpoint` | string | None | Checkpoint file for saving progress |
| `--resume` | string | None | Checkpoint file to resume from |
| `--chain` | list | None | Multiple guide files to chain |
| `--checkpoint-dir` | string | None | Directory for chain checkpoints |

*Required unless using `--dry-run`

### Examples

```bash
# Basic usage
python autonomous_ensemble.py --spec "Build a REST API" --guide coding_guide.txt

# Dry-run validation
python autonomous_ensemble.py --dry-run --guide my_guide.txt

# With custom config
python autonomous_ensemble.py --spec "..." --config custom.json --verbose

# Checkpoint and resume
python autonomous_ensemble.py --spec "..." --checkpoint progress.json
python autonomous_ensemble.py --spec "..." --resume progress.json

# Guide chaining
python autonomous_ensemble.py --spec "..." --chain guide1.txt guide2.txt guide3.txt
```

---

## Python API

### Config

Configuration dataclass for system settings.

```python
from autonomous_ensemble import Config

config = Config(
    ollama_api="http://localhost:11434/api/generate",
    model_a="qwen2.5-coder:7b",
    model_b="deepseek-coder-v2:16b",
    model_c="codestral:22b",
    temp_creative=0.8,
    temp_analytical=0.3,
    temp_adversarial=0.7,
    max_tokens=2000,
    max_iterations=3,
    output_file="final_output.txt",
    verbose=False
)

# Load from JSON
config = Config.from_json("config.json")
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `ollama_api` | str | `http://localhost:11434/api/generate` | Ollama API endpoint |
| `model_a` | str | `qwen2.5-coder:7b` | Creative model |
| `model_b` | str | `deepseek-coder-v2:16b` | Analytical model |
| `model_c` | str | `codestral:22b` | Adversarial model |
| `temp_creative` | float | 0.8 | Model A temperature |
| `temp_analytical` | float | 0.3 | Model B temperature |
| `temp_adversarial` | float | 0.7 | Model C temperature |
| `max_tokens` | int | 2000 | Maximum tokens per response |
| `max_iterations` | int | 3 | Max iterations for Model B/C |
| `output_file` | str | `final_output.txt` | Output file path |
| `verbose` | bool | False | Enable verbose logging |

---

### GuideLoader

Loads and parses guide files.

```python
from autonomous_ensemble import GuideLoader

loader = GuideLoader("coding_guide.txt")
steps = loader.load()  # Returns List[str]

for step in steps:
    print(step)
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `file_path: str` | None | Initialize with guide file path |
| `load` | None | `List[str]` | Parse guide and return steps |

#### Exceptions

- `FileNotFoundError`: Guide file doesn't exist
- `ValueError`: No valid steps found in guide

---

### WorkflowEngine

Main engine for running workflows.

```python
from autonomous_ensemble import Config, WorkflowEngine

config = Config()
engine = WorkflowEngine(config)

# Run workflow
result = engine.run(
    spec="Build a REST API",
    guide_file="coding_guide.txt"
)

# Dry-run validation
engine.dry_run("coding_guide.txt")
```

#### Constructor

```python
WorkflowEngine(
    config: Config,
    hooks: Optional[PipelineHooks] = None,
    checkpoint_file: Optional[str] = None
)
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `run` | `spec: str, guide_file: str, resume_from: str = None` | `str` | Run complete workflow |
| `dry_run` | `guide_file: str` | `None` | Validate guide without execution |

---

### GuideChain

Chain multiple guides together.

```python
from autonomous_ensemble import Config, GuideChain

config = Config()
chain = GuideChain(config, checkpoint_dir="./checkpoints")

# Run chain
result = chain.run(
    spec="Build a full application",
    guide_files=["coding.txt", "testing.txt", "deploy.txt"]
)

# Dry-run validation
chain.dry_run(["coding.txt", "testing.txt"])
```

#### Constructor

```python
GuideChain(
    config: Config,
    hooks: Optional[PipelineHooks] = None,
    checkpoint_dir: Optional[str] = None
)
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `run` | `spec: str, guide_files: List[str]` | `str` | Run all guides in sequence |
| `dry_run` | `guide_files: List[str]` | `None` | Validate all guides |

---

### PipelineHooks

Custom processing between pipeline stages.

```python
from autonomous_ensemble import PipelineHooks

def clean_output(text: str) -> str:
    return text.strip()

def add_header(text: str) -> str:
    return f"# Generated Code\n\n{text}"

hooks = PipelineHooks(
    post_draft=clean_output,
    post_correction=None,
    post_security=add_header
)
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `post_draft` | `Callable[[str], str]` | Hook after Model A |
| `post_correction` | `Callable[[str], str]` | Hook after Model B |
| `post_security` | `Callable[[str], str]` | Hook after Model C |

---

### Checkpoint

Save and restore workflow state.

```python
from autonomous_ensemble import Checkpoint

# Create checkpoint
checkpoint = Checkpoint(
    guide_file="coding_guide.txt",
    spec="My spec",
    completed_steps=5,
    cumulative_output="...",
    step_outputs=["step1", "step2", ...],
    timestamp="2024-01-01T12:00:00"
)

# Save to file
checkpoint.save("checkpoint.json")

# Load from file
restored = Checkpoint.load("checkpoint.json")
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | None | `dict` | Convert to dictionary |
| `from_dict` | `data: dict` | `Checkpoint` | Create from dictionary |
| `save` | `path: str` | `None` | Save to JSON file |
| `load` | `path: str` | `Checkpoint` | Load from JSON file |

---

### StateManager

Manages workflow state (internal use).

```python
from autonomous_ensemble import StateManager

state = StateManager()
state.add_step_output("Step 1 output")
state.add_step_output("Step 2 output")

context = state.get_context()  # Returns cumulative output
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `cumulative_output` | str | All step outputs concatenated |
| `current_step_index` | int | Current step number (0-indexed) |
| `step_outputs` | List[str] | Individual step outputs |

---

### StepContext

Context for processing a single step (internal use).

```python
from autonomous_ensemble import StepContext

context = StepContext(
    step_number=1,
    step_description="Implement user authentication",
    spec="Build a REST API",
    previous_output=""
)
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `step_number` | int | Current step number |
| `step_description` | str | Step instruction from guide |
| `spec` | str | Project specification |
| `previous_output` | str | Cumulative output so far |
| `draft` | str | Model A output |
| `corrected` | str | Model B output |
| `secured` | str | Model C output |

---

## Error Handling

### Exception Types

| Exception | Cause | Resolution |
|-----------|-------|------------|
| `FileNotFoundError` | Guide/config file missing | Check file path |
| `ValueError` | No valid steps in guide | Check guide format |
| `ConnectionError` | Can't reach Ollama API | Start Ollama server |
| `TimeoutError` | Model response timeout | Increase timeout or use smaller model |

### Example Error Handling

```python
from autonomous_ensemble import Config, WorkflowEngine

config = Config()
engine = WorkflowEngine(config)

try:
    result = engine.run("spec", "guide.txt")
except FileNotFoundError as e:
    print(f"File error: {e}")
except ConnectionError as e:
    print(f"API error: {e}")
except TimeoutError as e:
    print(f"Timeout: {e}")
```

---

## Configuration File Format

### JSON Schema

```json
{
  "ollama_api": "http://localhost:11434/api/generate",
  "model_a": "qwen2.5-coder:7b",
  "model_b": "deepseek-coder-v2:16b",
  "model_c": "codestral:22b",
  "temp_creative": 0.8,
  "temp_analytical": 0.3,
  "temp_adversarial": 0.7,
  "max_tokens": 2000,
  "max_iterations": 3,
  "output_file": "output.txt",
  "verbose": true
}
```

### Guide File Format

```
Step 1: First instruction
Step 2: Second instruction
Step 3: Third instruction
...
Step N: Final instruction
```

- One step per line
- Format: `Step {number}: {description}`
- Case-insensitive (`Step`, `STEP`, `step` all work)
- Steps are sorted by number
