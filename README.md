# Autonomous Coding Ensemble System
## Technical Specification v1.0

---

## 1. System Overview

**Purpose:** A local, autonomous multi-model ensemble that processes coding tasks through a swappable guide-driven workflow. Three specialized LLMs collaborate sequentially—creative drafting, analytical correction, and adversarial security scanning—to produce quality-checked output without human intervention.

**Core Philosophy:** Quality through enforced iteration. Every artifact passes through multiple validation layers before accumulation into the final output.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WORKFLOW ENGINE                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │  Guide   │───▶│  Step    │───▶│  State   │                  │
│  │  Loader  │    │  Parser  │    │  Manager │                  │
│  └──────────┘    └──────────┘    └──────────┘                  │
├─────────────────────────────────────────────────────────────────┤
│                      PROCESSING PIPELINE                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │ Model A  │───▶│ Model B  │───▶│ Model C  │                  │
│  │ Creative │    │ Analyst  │    │ Adversary│                  │
│  │ (Draft)  │    │ (Correct)│    │ (Secure) │                  │
│  └──────────┘    └──────────┘    └──────────┘                  │
│       │               │               │                         │
│       └───────────────┴───────────────┘                         │
│                       ▼                                         │
│              ┌──────────────┐                                   │
│              │  Accumulator │──▶ final_output.txt               │
│              └──────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │   Ollama API     │
              │ localhost:11434  │
              └──────────────────┘
```

---

## 3. Component Specifications

### 3.1 Guide Loader

| Property | Specification |
|----------|---------------|
| Input | Text file path (e.g., `coding_guide.txt`) |
| Format | One step per line, prefix `Step N:` |
| Validation | Must contain ≥1 valid step line |
| Output | Ordered list of step descriptions |

**Step Line Pattern:**
```
Step {integer}: {description}
```

### 3.2 Model Pipeline

| Model | Role | Temperature | Purpose |
|-------|------|-------------|---------|
| **Model A** | Creative | 0.8 (high) | Generate initial draft/code for current step |
| **Model B** | Analytical | 0.3 (low) | Error detection, bug fixes, efficiency improvements |
| **Model C** | Adversarial | 0.7 (medium) | Security vulnerability scanning, exploit identification |

**Recommended Models (Ollama):**
- Model A: `qwen2.5-coder:7b`
- Model B: `deepseek-coder-v2:16b`
- Model C: `codestral:22b`

### 3.3 Iteration Controller

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_correction_iterations` | 3 | Model B retry limit per step |
| `max_security_iterations` | 3 | Model C retry limit per step |
| `convergence_check` | Output equality | Stop iterating when output unchanged |

### 3.4 State Manager

| State Variable | Type | Purpose |
|----------------|------|---------|
| `cumulative_output` | string | Concatenated output from all completed steps |
| `current_step_index` | integer | Progress tracker (1-indexed) |
| `step_outputs[]` | array | Individual step results for granular access |

---

## 4. Data Structures

### 4.1 Configuration Object

```python
Config = {
    "ollama_api": str,           # Default: "http://localhost:11434/api/generate"
    "model_a": str,              # Creative model identifier
    "model_b": str,              # Analytical model identifier  
    "model_c": str,              # Adversarial model identifier
    "temp_creative": float,      # Default: 0.8
    "temp_analytical": float,    # Default: 0.3
    "temp_adversarial": float,   # Default: 0.7
    "max_tokens": int,           # Default: 2000
    "max_iterations": int,       # Default: 3
    "output_file": str           # Default: "final_output.txt"
}
```

### 4.2 Step Processing Context

```python
StepContext = {
    "step_number": int,
    "step_description": str,
    "spec": str,
    "previous_output": str,
    "draft": str,
    "corrected": str,
    "secured": str
}
```

### 4.3 API Request Payload

```python
OllamaRequest = {
    "model": str,
    "prompt": str,
    "options": {
        "temperature": float
    },
    "stream": bool,              # Always False for this system
    "max_tokens": int
}
```

---

## 5. Processing Logic

### 5.1 Main Workflow Loop

```
FUNCTION run_workflow(spec, guide_file):
    steps ← load_guide(guide_file)
    cumulative_output ← ""
    
    FOR i, step IN enumerate(steps):
        step_output ← process_step(step, spec, cumulative_output)
        cumulative_output ← cumulative_output + format_step_output(i, step_output)
        log_progress(i, len(steps))
    
    write_file(output_file, cumulative_output)
```

### 5.2 Step Processing Pipeline

```
FUNCTION process_step(step_desc, spec, previous_output):
    context ← build_context(previous_output)
    
    # Stage 1: Creative Draft
    draft ← query_model_a(context, step_desc, spec)
    
    # Stage 2: Error Correction (iterative)
    corrected ← draft
    FOR i IN range(max_iterations):
        new_corrected ← query_model_b(context, corrected)
        IF new_corrected == corrected:
            BREAK
        corrected ← new_corrected
    
    # Stage 3: Security Hardening (iterative)
    secured ← corrected
    FOR i IN range(max_iterations):
        new_secured ← query_model_c(context, secured)
        IF new_secured == secured:
            BREAK
        secured ← new_secured
    
    RETURN secured
```

---

## 6. Prompt Templates

### 6.1 Model A (Creative Draft)

```
{context}
Apply this step to the spec '{spec}': {step_description}
Generate a creative draft of code or plan.
```

### 6.2 Model B (Error Correction)

```
{context}
Strictly analyze this for errors, bugs, inefficiencies:
{current_output}
Correct without adding new features.
```

### 6.3 Model C (Security Scan)

```
{context}
Act as a hacker: Identify security flaws in the following and suggest fixes:
{current_output}
List vulnerabilities and provide corrected code.
```

---

## 7. File Specifications

### 7.1 Guide File Format

**Filename Pattern:** `*_guide.txt`

**Structure:**
```
Step 1: [Action description]
Step 2: [Action description]
...
Step N: [Action description]
```

**Example - Coding Guide (`coding_guide.txt`):**
```
Step 1: Analyze the project spec and outline high-level requirements.
Step 2: Define the system architecture and components.
Step 3: Set up the development environment and dependencies.
Step 4: Design database schema and data models.
Step 5: Implement core business logic modules.
...
Step 40: Final integration testing and deployment preparation.
```

**Example - Post-Coding Guide (`post_coding_guide.txt`):**
```
Step 1: Run syntax checks and fix compilation errors.
Step 2: Execute unit tests and debug failures.
Step 3: Scan for common vulnerabilities (SQL injection, XSS, CSRF).
Step 4: Profile memory usage and fix leaks.
Step 5: Optimize hot paths and reduce complexity.
...
Step 40: Final security audit and penetration test review.
```

### 7.2 Output File Format

**Filename:** `final_output.txt` (configurable)

**Structure:**
```
--- Step 1 Output ---
[Model C final output for step 1]

--- Step 2 Output ---
[Model C final output for step 2]

...

--- Step N Output ---
[Model C final output for step N]
```

---

## 8. Error Handling

| Error Type | Trigger | Response |
|------------|---------|----------|
| `FileNotFoundError` | Guide file missing | Exit with message, list available guides |
| `ValueError` | No valid steps in guide | Exit with format instructions |
| `ConnectionError` | Ollama API unreachable | Retry 3x with backoff, then exit |
| `ModelError` | Invalid model name | Exit with available models list |
| `TimeoutError` | Model response timeout | Retry current step, log warning |

---

## 9. CLI Interface

```
usage: autonomous_ensemble.py [-h] --spec SPEC [--guide GUIDE] [--output OUTPUT]

Arguments:
  --spec SPEC       Project specification (string or file path)
  --guide GUIDE     Path to guide file (default: coding_guide.txt)
  --output OUTPUT   Output file path (default: final_output.txt)
  --config CONFIG   Optional JSON config file for model overrides
  --verbose         Enable detailed logging
  --dry-run         Parse guide and validate without running models
```

---

## 10. Extension Points

### 10.1 Custom Model Hooks

Allow injection of custom processing functions between pipeline stages:

```python
hooks = {
    "post_draft": callable,      # After Model A, before Model B
    "post_correction": callable, # After Model B, before Model C
    "post_security": callable    # After Model C, before accumulation
}
```

### 10.2 Guide Chaining

Support sequential execution of multiple guides:

```python
chain = ["coding_guide.txt", "testing_guide.txt", "deploy_guide.txt"]
# Output of guide N becomes input context for guide N+1
```

### 10.3 Checkpoint/Resume

Save state after each step to enable resumption:

```python
checkpoint = {
    "guide_file": str,
    "completed_steps": int,
    "cumulative_output": str,
    "timestamp": datetime
}
```

---

## 11. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | ≥3.8 | Runtime |
| requests | (stdlib-compatible) | HTTP client for Ollama API |
| json | (stdlib) | Payload serialization |
| os | (stdlib) | File operations |
| argparse | (stdlib) | CLI parsing |

**External Requirement:** Ollama running locally with specified models pulled.

---

## 12. Performance Considerations

| Factor | Recommendation |
|--------|----------------|
| Step count | Start with 5-10 steps for testing |
| Token limit | 2000 default; increase for complex outputs |
| Context growth | Monitor cumulative_output size; truncate oldest if needed |
| Model loading | First query per model incurs load time |
| Parallel processing | Not recommended (context dependency between steps) |

---

## 13. Security Notes

- All processing is local (no external API calls beyond localhost)
- Spec and output files should be treated as potentially sensitive
- Model C's "hacker perspective" prompts should not be exposed to untrusted input
- Output should be reviewed before execution in production environments

---

*Specification complete. Ready for implementation.*
