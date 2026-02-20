# Security Audit Remediation Plan

Addresses all 13 findings from `SECURITY_AUDIT.md` (Agentic Security Audit, 2026-02-20).

---

## Phase 1 — Configuration Quick Wins (no code changes)

**Scope:** 4 files, config-only changes. Zero risk to application behavior.

### 1a. Pin dependency versions (T3-02 — MEDIUM)

**Files:** `requirements.txt`, `requirements-dev.txt`

Replace floor pins (`>=`) with exact pins (`==`) to prevent supply-chain attacks
via compromised newer versions.

```
# requirements.txt
requests==2.32.3
python-dotenv==1.0.1

# requirements-dev.txt
flake8==7.1.1
mypy==1.14.1
bandit==1.8.3
pytest==8.3.4
pytest-cov==6.0.0
```

Keep `>=` in `pyproject.toml` for library compatibility metadata.

### 1b. Make bandit block CI on failure (T3-03 — MEDIUM)

**File:** `.github/workflows/ci.yml:42-43`

Remove `continue-on-error: true` from the bandit step so security findings fail
the build. Keep `continue-on-error` on mypy (type errors are informational).

### 1c. Pin CI tool versions (T3-04 — LOW)

**File:** `.github/workflows/ci.yml:28`

Change:
```yaml
pip install flake8 mypy bandit
```
To:
```yaml
pip install flake8==7.1.1 mypy==1.14.1 bandit==1.8.3
```

### 1d. Bind Ollama port to localhost only (T3-05 — LOW)

**File:** `docker-compose.yml:9`

Change:
```yaml
- "11434:11434"
```
To:
```yaml
- "127.0.0.1:11434:11434"
```

---

## Phase 2 — Input/Output Hardening (code changes)

**Scope:** `autonomous_ensemble.py` — ~80 lines added/changed. Low risk.

### 2a. Path canonicalization for spec files (T2-05 — MEDIUM)

**Location:** `autonomous_ensemble.py:568-572` — `WorkflowEngine.run()`

Before reading a spec file, canonicalize the path with `os.path.realpath()` and
verify it resolves within the current working directory (or a configured allowed
base). Reject paths that escape the boundary.

```python
spec_content = spec
if os.path.isfile(spec):
    real_path = os.path.realpath(spec)
    allowed_base = os.path.realpath(os.getcwd())
    if not real_path.startswith(allowed_base + os.sep) and real_path != allowed_base:
        raise ValueError(
            f"Spec file path resolves outside working directory: {real_path}"
        )
    with open(real_path, "r") as f:
        spec_content = f.read()
```

### 2b. Validate output file paths (T2-06 — LOW)

**Locations:** `autonomous_ensemble.py:627`, `:751`, `:771`, `:315`

Add a helper function that canonicalizes output paths and rejects any that resolve
outside the working directory. Call it before every `open(..., "w")` for output
and checkpoint files.

```python
def _validate_output_path(path: str) -> str:
    """Resolve path and reject if outside working directory."""
    real_path = os.path.realpath(path)
    allowed_base = os.path.realpath(os.getcwd())
    if not real_path.startswith(allowed_base + os.sep) and real_path != allowed_base:
        raise ValueError(f"Output path resolves outside working directory: {real_path}")
    return real_path
```

### 2c. Output secret scanning (T2-04 — MEDIUM)

**Location:** `autonomous_ensemble.py` — new `OutputScanner` class, called before
writing output at lines 627 and 771.

Scan model output for high-confidence secret patterns before writing to disk.
Log warnings but do not block (false positives are possible with generated code).

Patterns to detect:
- API keys: `(api[_-]?key|secret[_-]?key)\s*=\s*["'][^"']{20,}["']`
- Tokens: `(token|auth[_-]?token|bearer)\s*=\s*["'][a-zA-Z0-9]{20,}["']`
- Private key blocks: `-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----`

### 2d. Checkpoint HMAC integrity (T2-03 — MEDIUM)

**Location:** `autonomous_ensemble.py:313-323` — `Checkpoint.save()` and `.load()`

Add HMAC-SHA256 verification:
- On `save()`: compute HMAC of the JSON content, write to `<path>.hmac`
- On `load()`: if `.hmac` file exists, verify before deserializing; warn if missing

Key sourced from `CHECKPOINT_SECRET` env var, defaulting to `"code-cobra-local"`.

New imports: `hashlib`, `hmac` (both stdlib, zero new dependencies).

---

## Phase 3 — Prompt Security (code changes)

**Scope:** `autonomous_ensemble.py:514-538` — ~40 lines changed. Low risk.

### 3a. Data/instruction delimiters in prompts (T2-01 — MEDIUM)

**Location:** `_build_creative_prompt`, `_build_correction_prompt`,
`_build_security_prompt`

Wrap user-supplied content (spec, previous output) in explicit XML-style delimiter
tags to create clear boundaries between system instructions and user data:

```python
def _build_creative_prompt(self, context: StepContext) -> str:
    return (
        "You are a code generation assistant. Follow the instruction below.\n\n"
        f"<instruction>\n"
        f"Apply this step: {context.step_description}\n"
        f"</instruction>\n\n"
        f"<user_specification>\n"
        f"{context.spec}\n"
        f"</user_specification>\n\n"
        f"<previous_context>\n"
        f"{context.previous_output}\n"
        f"</previous_context>\n\n"
        "Generate a creative draft of code or plan."
    )
```

Same pattern for correction and security prompts.

### 3b. Prompt injection detection (T2-02 — MEDIUM)

**Location:** `autonomous_ensemble.py` — after spec loading (~line 572)

Add a lightweight check for common prompt injection patterns in spec content.
Log warnings (don't block — false positives are possible).

Patterns:
- `ignore (previous|above|all) instructions`
- `(system|assistant):`
- `you are now`
- `</?system` or `</?instruction` or `</?prompt` tags

---

## Phase 4 — Documentation & Logging

**Scope:** 2 files, additive changes only. Zero risk.

### 4a. Structured audit logging (T3-01 — LOW)

**Location:** `autonomous_ensemble.py` — new `AuditLogger` class

Add an append-only JSON-lines (`audit.jsonl`) logger that records pipeline events:
`workflow_start`, `step_start`, `stage_draft`, `stage_correction`, `stage_security`,
`step_complete`, `workflow_complete`, `checkpoint_saved`.

Each entry includes: timestamp, event name, step number, model used, and status.

### 4b. Document per-module access expectations (T1-01, T1-02 — LOW)

**File:** `docs/SECURITY.md`

Add a "Component Access Model" section documenting what each module is permitted
to access (file system paths, network endpoints), and the checkpoint integrity
model.

---

## Implementation Order

| Step | Finding(s) | Phase | Files Changed | Risk |
|------|-----------|-------|---------------|------|
| 1 | T3-02 | 1a | `requirements.txt`, `requirements-dev.txt` | None |
| 2 | T3-03, T3-04 | 1b+1c | `.github/workflows/ci.yml` | None |
| 3 | T3-05 | 1d | `docker-compose.yml` | None |
| 4 | T2-05, T2-06 | 2a+2b | `autonomous_ensemble.py` | Low |
| 5 | T2-04 | 2c | `autonomous_ensemble.py` | Low |
| 6 | T2-03 | 2d | `autonomous_ensemble.py` | Low |
| 7 | T2-01, T2-02 | 3a+3b | `autonomous_ensemble.py` | Low |
| 8 | T3-01 | 4a | `autonomous_ensemble.py` | None |
| 9 | T1-01, T1-02 | 4b | `docs/SECURITY.md` | None |

Each step is one commit. Phase 1 can be merged immediately. Phases 2-3 should
include corresponding test additions.

## Testing Strategy

**Phase 1:** No code changes — verify CI pipeline passes.

**Phase 2 tests** (add to `tests/test_security.py`):
- Path traversal with `../` in spec path is rejected
- Path traversal with `../` in output path is rejected
- `OutputScanner` detects API key patterns in content
- `OutputScanner` detects private key blocks in content
- Checkpoint with valid HMAC loads successfully
- Checkpoint with tampered content raises `ValueError`
- Checkpoint without HMAC file logs warning but loads

**Phase 3 tests** (add to `tests/test_security.py`):
- Built prompts contain `<user_specification>` delimiters
- Built prompts contain `<instruction>` delimiters
- Injection pattern "ignore previous instructions" triggers warning log
- Clean spec content does not trigger false positive warnings

**Phase 4:** Verify `audit.jsonl` is created and contains expected event types
after a dry-run or mocked workflow.
