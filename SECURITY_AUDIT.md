# Code Cobra — Agentic Security Audit Report

**Audit Date:** 2026-02-20
**Methodology:** [Agentic Security Audit Checklist](https://github.com/kase1111-hash/Claude-prompts/blob/main/Agentic-Security-Audit.md)
**Auditor:** Claude (Automated Analysis)
**Version Audited:** 1.0.1
**Scope:** Full repository — source, config, CI/CD, Docker, dependencies, git history

---

## Executive Summary

This audit applies the three-tier Agentic Security Audit framework to Code Cobra, a multi-agent AI coding system that orchestrates local Ollama LLMs through a three-stage pipeline (creative draft, error correction, security hardening).

| Tier | Scope | Findings | Status |
|------|-------|----------|--------|
| **Tier 1** — Immediate Wins | Credential storage, permissions, identity | 2 findings | Partially addressed |
| **Tier 2** — Core Enforcement | Input gates, memory integrity, secret scanning, signing | 6 findings | Gaps identified |
| **Tier 3** — Protocol Maturity | Audit trails, mutual auth, anti-C2, coordination | 5 findings | Not yet implemented |

**Overall Risk Rating:** MEDIUM — No critical exploitable vulnerabilities, but several hardening gaps exist around file path validation, checkpoint integrity, output scanning, and dependency pinning that should be addressed before deploying in any shared or adversarial environment.

---

## Tier 1 — Immediate Wins (Architectural Defaults)

### 1.1 Credential Storage

| Check | Result | Details |
|-------|--------|---------|
| Plaintext secrets in source code | PASS | No hardcoded passwords, API keys, or tokens found in any `.py`, `.sh`, `.yml`, `.json`, or `.toml` file |
| Secrets in git history | PASS | `git log --all -p` shows no `.env`, `.pem`, `.key`, or credential files ever committed |
| `.env` excluded from version control | PASS | `.gitignore` correctly excludes `.env`, `.env.local`, `.env.*.local` |
| `.env.example` free of real secrets | PASS | Contains only default localhost URLs and model names |
| Secrets in Docker layers | PASS | No `COPY .env`, `ENV SECRET`, or credential `ARG`s in `Dockerfile` |
| Secrets in CI/CD environment | PASS | `ci.yml` does not reference secrets or environment variables with credentials |

**Status:** PASS — Credential hygiene is clean.

### 1.2 Default-Deny Permissions

| Check | Result | Details |
|-------|--------|---------|
| Docker runs as non-root | PASS | `Dockerfile:38` — `USER appuser` after `useradd` |
| No privileged containers | PASS | `docker-compose.yml` contains no `privileged`, `cap_add`, or `security_opt` directives |
| File permissions controlled | PASS | `Dockerfile:35` — `chown -R appuser:appuser /app` |
| Guide volumes mounted read-only | PASS | `docker-compose.yml:34` — `./guides:/app/guides:ro` |
| Per-module capability declarations | **FINDING-T1-01** | No explicit capability/permission manifests per component |

#### FINDING-T1-01: No Per-Module Capability Declarations

**Severity:** LOW
**Location:** System-wide (architectural)

The codebase has no formal mechanism declaring what resources each module is permitted to access. `GuideLoader` can open any file path, `WorkflowEngine` can write to any output path, and `OllamaClient` can connect to any URL provided in config. While acceptable for a local-only tool, this creates implicit trust assumptions.

**Recommendation:** Document expected file system and network access per component in `docs/SECURITY.md`. Consider validating that `ollama_api` URLs are restricted to localhost/internal hostnames.

### 1.3 Cryptographic Agent Identity

| Check | Result | Details |
|-------|--------|---------|
| Keypair-based agent authentication | **FINDING-T1-02** | Not implemented |
| Signed outputs or checkpoints | N/A | No cryptographic signing |
| Any cryptographic usage | N/A | No `hashlib`, `hmac`, `bcrypt`, or `cryptography` imports |

#### FINDING-T1-02: No Cryptographic Agent or Checkpoint Identity

**Severity:** LOW
**Location:** System-wide

No cryptographic identity exists for the agent or its outputs. Checkpoint files (`Checkpoint.save()` at `autonomous_ensemble.py:313`) are plain JSON without integrity verification. Guide files are loaded without signature checks.

**Recommendation:** For environments where checkpoint or guide file tampering is a concern, add HMAC-based integrity checks to checkpoint files and consider signing guide files.

---

## Tier 2 — Core Enforcement Layer

### 2.1 Input Classification Gate

| Check | Result | Details |
|-------|--------|---------|
| Data/instruction separation at preprocessing | **FINDING-T2-01** | Not implemented |
| Instruction-like pattern detection in external content | **FINDING-T2-02** | Not implemented |
| Guide file format validation | PASS | `GuideLoader` uses strict regex `^Step\s+(\d+):\s*(.+)$` at `autonomous_ensemble.py:160` |
| Duplicate step detection | PASS | `autonomous_ensemble.py:193-202` raises `ValueError` on duplicates |

#### FINDING-T2-01: No Data/Instruction Separation in Prompts

**Severity:** MEDIUM
**Location:** `autonomous_ensemble.py:514-538` (`_build_creative_prompt`, `_build_correction_prompt`, `_build_security_prompt`)

User-supplied specification text (`context.spec`) and previous model output (`context.previous_output`) are concatenated directly into prompts without any delimiter or role-based separation. A malicious specification could contain prompt injection text that alters model behavior.

```python
# autonomous_ensemble.py:516-520
def _build_creative_prompt(self, context: StepContext) -> str:
    return (
        f"{context.previous_output}\n"
        f"Apply this step to the spec '{context.spec}': {context.step_description}\n"
        f"Generate a creative draft of code or plan."
    )
```

**Recommendation:** Use clear delimiters (e.g., `<user_specification>...</user_specification>`) and system-level instructions before user content. Add input sanitization to flag instruction-like patterns in specifications.

#### FINDING-T2-02: No Prompt Injection Detection for External Content

**Severity:** MEDIUM
**Location:** `autonomous_ensemble.py:456-466` (`_creative_draft`)

When `spec` is loaded from a file (`autonomous_ensemble.py:570-572`), the file content is passed directly as prompt input. If the spec file comes from an untrusted source, it could contain adversarial prompt instructions.

**Recommendation:** Add a classification pass that flags specification content containing instruction-like patterns (e.g., "ignore previous instructions", "system:", role-switching keywords).

### 2.2 Memory Integrity

| Check | Result | Details |
|-------|--------|---------|
| Memory entries tagged with provenance | **FINDING-T2-03** | No provenance tracking |
| Untrusted source quarantine | N/A | All sources treated equally |
| Modification detection via hashing | NOT IMPLEMENTED | No integrity verification |

#### FINDING-T2-03: Checkpoint Files Have No Integrity Verification

**Severity:** MEDIUM
**Location:** `autonomous_ensemble.py:313-323` (`Checkpoint.save()`, `Checkpoint.load()`)

Checkpoint files are serialized as plain JSON via `json.dump()` and deserialized via `json.load()`. While JSON deserialization is safe (unlike pickle), there is no integrity check to detect tampering. A modified checkpoint could cause the workflow to resume from a corrupted state, potentially producing manipulated output.

```python
# autonomous_ensemble.py:318-322
@classmethod
def load(cls, path: str) -> "Checkpoint":
    with open(path, "r") as f:
        data = json.load(f)
    return cls.from_dict(data)
```

**Recommendation:** Add an HMAC digest field to checkpoint files. Compute the HMAC over the serialized JSON content on save, and verify it on load.

### 2.3 Outbound Secret Scanning

| Check | Result | Details |
|-------|--------|---------|
| Output scanned for credentials before writing | **FINDING-T2-04** | Not implemented |
| Pattern matching on model responses | NOT IMPLEMENTED | Responses written directly to file |
| Entropy detection on output | NOT IMPLEMENTED | No entropy checks |

#### FINDING-T2-04: No Secret Scanning on Model Output

**Severity:** MEDIUM
**Location:** `autonomous_ensemble.py:627-628` (`WorkflowEngine.run()`)

Model output is written directly to the output file without scanning for accidentally-generated credentials, API keys, or sensitive patterns. The existing `scripts/backdoor_check.py` scanner is only designed for manual post-hoc analysis and is not integrated into the pipeline.

```python
# autonomous_ensemble.py:627-628
with open(self.config.output_file, "w") as f:
    f.write(self.state.cumulative_output)
```

**Recommendation:** Run the backdoor checker patterns (or a subset) against model output before writing to disk. At minimum, scan for high-entropy strings and common credential patterns.

### 2.4 Skill/Module Signing

| Check | Result | Details |
|-------|--------|---------|
| Cryptographic guide file signatures | NOT IMPLEMENTED | Guide files loaded by filename only |
| Resource access manifests | NOT IMPLEMENTED | No declared access requirements |
| Sandboxed execution | PARTIAL | Docker provides container-level isolation |

### 2.5 Path Traversal and File Access Controls

| Check | Result | Details |
|-------|--------|---------|
| Spec file path validation | **FINDING-T2-05** | No path canonicalization |
| Output file path validation | **FINDING-T2-06** | No boundary checks |
| Guide file path validation | PARTIAL | Checks existence but no path restriction |

#### FINDING-T2-05: Spec File Path Lacks Canonicalization

**Severity:** MEDIUM
**Location:** `autonomous_ensemble.py:570-572`

When the `--spec` argument points to a file, `os.path.isfile(spec)` is used to detect this and read the file. No path canonicalization (`os.path.realpath()`) or boundary checking is performed. A spec path like `--spec ../../../../etc/passwd` would be read if the file exists.

```python
# autonomous_ensemble.py:570-572
if os.path.isfile(spec):
    with open(spec, "r") as f:
        spec_content = f.read()
```

**Recommendation:** Canonicalize the path with `os.path.realpath()` and optionally restrict to the project directory or an allowed list of directories.

#### FINDING-T2-06: Output File Path Not Validated

**Severity:** LOW
**Location:** `autonomous_ensemble.py:627`, `autonomous_ensemble.py:751`, `autonomous_ensemble.py:771`

Output file paths come from config or CLI (`--output`) without validation. A user (or compromised config) could specify paths like `/etc/cron.d/malicious` to write arbitrary files.

**Recommendation:** Validate output paths are within the expected output directory. Refuse absolute paths or paths containing `..`.

---

## Tier 3 — Protocol-Level Maturity

### 3.1 Constitutional Audit Trail

| Check | Result | Details |
|-------|--------|---------|
| Append-only decision logging | **FINDING-T3-01** | Not implemented |
| Reasoning chain preservation | PARTIAL | Verbose mode prints to stdout, not persisted |
| Tamper-evident log storage | NOT IMPLEMENTED | Standard Python logging only |

#### FINDING-T3-01: No Append-Only Audit Trail

**Severity:** LOW
**Location:** `autonomous_ensemble.py:24-25`

Logging uses standard Python `logging.basicConfig()` at INFO level. There is no structured, append-only audit log that captures:
- Which model produced which output
- Convergence decisions (when iterations stopped)
- Full prompt/response pairs for reproducibility

**Recommendation:** Add a structured JSON audit log that records each pipeline stage's input/output, model used, convergence status, and timestamps. Store as an append-only file with rotation.

### 3.2 Mutual Agent Authentication

| Check | Result | Details |
|-------|--------|---------|
| Challenge-response between models | NOT IMPLEMENTED | Models are accessed via plain HTTP to Ollama |
| Model identity verification | NOT IMPLEMENTED | No verification that the correct model responded |

This is expected for the current architecture (single Ollama server). Relevant if the system evolves to use remote or federated model endpoints.

### 3.3 Anti-C2 Pattern Enforcement

| Check | Result | Details |
|-------|--------|---------|
| No fetch-and-execute patterns | PASS | No `curl | sh`, no dynamic code download/execution |
| Dependency pinning | **FINDING-T3-02** | Floor-pinned only (`>=`), not exact (`==`) |
| Human approval for updates | N/A | No auto-update mechanism |

#### FINDING-T3-02: Dependencies Use Floor Pinning, Not Exact Pinning

**Severity:** MEDIUM
**Location:** `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`

All dependencies use floor version constraints (`>=`), which means `pip install` will pull the latest compatible version. This creates a supply-chain risk if a dependency is compromised in a newer version.

```
# requirements.txt
requests>=2.28.0       # Could install 2.99.0
python-dotenv>=1.0.0   # Could install 1.99.0
```

**Recommendation:** Pin exact versions in `requirements.txt` (e.g., `requests==2.32.3`) and use a lock file (`pip freeze > requirements.lock`). Keep `>=` in `pyproject.toml` for library compatibility, but pin for application deployments.

### 3.4 CI/CD Security

| Check | Result | Details |
|-------|--------|---------|
| Security scans block pipeline | **FINDING-T3-03** | Bandit and mypy set to `continue-on-error: true` |
| CI dependencies pinned | **FINDING-T3-04** | Dev tools installed without version pins |
| Signed release artifacts | NOT IMPLEMENTED | Artifacts uploaded unsigned |

#### FINDING-T3-03: Security Scan Failures Do Not Block CI

**Severity:** MEDIUM
**Location:** `.github/workflows/ci.yml:37-38, 42-43`

Both `mypy` (type checking) and `bandit` (security scanning) have `continue-on-error: true`, meaning security findings and type errors will not fail the build.

```yaml
# .github/workflows/ci.yml:37-43
- name: Type check with mypy
  run: mypy autonomous_ensemble.py --ignore-missing-imports
  continue-on-error: true

- name: Security scan with bandit
  run: bandit -r autonomous_ensemble.py -ll
  continue-on-error: true
```

**Recommendation:** Remove `continue-on-error: true` from at least the `bandit` security scan step. Bandit findings at medium-low (`-ll`) or higher should block merges.

#### FINDING-T3-04: CI Installs Unpinned Development Tools

**Severity:** LOW
**Location:** `.github/workflows/ci.yml:28`

The CI pipeline installs `flake8`, `mypy`, and `bandit` without version pins:

```yaml
pip install flake8 mypy bandit
```

A compromised version of any of these tools could execute arbitrary code in the CI environment.

**Recommendation:** Pin these to exact versions: `pip install flake8==7.1.1 mypy==1.13.0 bandit==1.8.0` (or current known-good versions).

### 3.5 Docker Compose Network Exposure

| Check | Result | Details |
|-------|--------|---------|
| Ollama port exposure | **FINDING-T3-05** | Port 11434 mapped to host |
| Container network isolation | PARTIAL | Default bridge network |

#### FINDING-T3-05: Ollama Port Exposed to Host Network

**Severity:** LOW
**Location:** `docker-compose.yml:8-9`

The Ollama service maps port 11434 to the host:

```yaml
ports:
  - "11434:11434"
```

This makes the Ollama API accessible to any process on the host (and potentially the network, depending on firewall rules). Since the `code-cobra` container communicates with Ollama via the Docker network (`http://ollama:11434`), host-side port mapping is unnecessary for production use.

**Recommendation:** Remove the `ports` mapping and rely on the internal Docker network for inter-container communication. If host access is needed for debugging, bind to localhost only: `"127.0.0.1:11434:11434"`.

---

## Tier 2/3 — Vibe-Code Security Review (Automated Scan Results)

### Pattern Scan Results

| Pattern | Files Scanned | Findings |
|---------|--------------|----------|
| Hardcoded credentials (password, api_key, token) | All `.py`, `.sh`, `.yml`, `.json` | 0 |
| Code injection (`eval`, `exec`, `__import__`, `os.system`) | All `.py` (excluding tests) | 0 in production code |
| Insecure deserialization (`pickle.load`, `yaml.load`) | All `.py` (excluding tests) | 0 |
| TLS bypass (`verify=False`, `CERT_NONE`) | All `.py` | 0 |
| Reverse shell patterns | All `.py`, `.sh` | 0 |
| Base64+exec obfuscation | All `.py` | 0 |
| Fetch-and-execute in CI | All `.yml` | 0 |
| Private keys in repo | Full repo | 0 |
| Secrets in git history | Full history | 0 |

### Network Usage

| Location | Protocol | Destination | Purpose |
|----------|----------|-------------|---------|
| `autonomous_ensemble.py:367` | HTTP POST | `config.ollama_api` (default: `localhost:11434`) | LLM inference |

No other outbound network calls exist in production code. The single HTTP endpoint is configurable, defaults to localhost, and has retry logic with exponential backoff.

---

## Consolidated Findings Summary

| ID | Severity | Tier | Finding | Location |
|----|----------|------|---------|----------|
| T1-01 | LOW | 1 | No per-module capability declarations | System-wide |
| T1-02 | LOW | 1 | No cryptographic agent/checkpoint identity | System-wide |
| T2-01 | MEDIUM | 2 | No data/instruction separation in prompts | `autonomous_ensemble.py:514-538` |
| T2-02 | MEDIUM | 2 | No prompt injection detection for external content | `autonomous_ensemble.py:456-466` |
| T2-03 | MEDIUM | 2 | Checkpoint files have no integrity verification | `autonomous_ensemble.py:313-323` |
| T2-04 | MEDIUM | 2 | No secret scanning on model output | `autonomous_ensemble.py:627-628` |
| T2-05 | MEDIUM | 2 | Spec file path lacks canonicalization | `autonomous_ensemble.py:570-572` |
| T2-06 | LOW | 2 | Output file path not validated | `autonomous_ensemble.py:627, 751, 771` |
| T3-01 | LOW | 3 | No append-only audit trail | `autonomous_ensemble.py:24-25` |
| T3-02 | MEDIUM | 3 | Dependencies use floor pinning, not exact | `requirements.txt` |
| T3-03 | MEDIUM | 3 | Security scan failures do not block CI | `.github/workflows/ci.yml:37-43` |
| T3-04 | LOW | 3 | CI installs unpinned dev tools | `.github/workflows/ci.yml:28` |
| T3-05 | LOW | 3 | Ollama port exposed to host network | `docker-compose.yml:8-9` |

**Severity Distribution:** 0 CRITICAL, 0 HIGH, 7 MEDIUM, 6 LOW

---

## Prioritized Remediation Plan

### Phase 1 — Quick Wins (Configuration Changes)

1. **Pin dependency versions** (T3-02) — Create `requirements.lock` with exact versions
2. **Remove `continue-on-error`** from bandit in CI (T3-03)
3. **Pin CI tool versions** (T3-04) — Specify exact versions for flake8, mypy, bandit
4. **Bind Ollama port to localhost** (T3-05) — Change to `127.0.0.1:11434:11434`

### Phase 2 — Input/Output Hardening (Code Changes)

5. **Add path canonicalization** (T2-05) — Use `os.path.realpath()` and boundary checks on spec/guide paths
6. **Validate output file paths** (T2-06) — Restrict to project directory or configured output dir
7. **Add output secret scanning** (T2-04) — Run pattern scan on model output before writing to disk
8. **Add checkpoint integrity** (T2-03) — HMAC verification on checkpoint save/load

### Phase 3 — Prompt Security (Architecture Changes)

9. **Add data/instruction delimiters** (T2-01) — Wrap user content in explicit tags
10. **Add injection detection** (T2-02) — Flag instruction-like patterns in spec content
11. **Add structured audit logging** (T3-01) — JSON-format append-only log per workflow run

### Phase 4 — Documentation

12. **Document per-module access expectations** (T1-01) — Update `docs/SECURITY.md`
13. **Document checkpoint security model** (T1-02) — Add integrity verification guidance

---

## Strengths Identified

The following security practices are already well-implemented:

- **Clean credential hygiene** — No secrets in source, git history, Docker layers, or CI
- **Minimal attack surface** — Only 2 production dependencies (`requests`, `python-dotenv`)
- **Container security** — Non-root user, no privileged containers, read-only guide mounts
- **No dangerous code patterns** — Zero `eval`, `exec`, `pickle`, `subprocess shell=True` in production code
- **Existing security tooling** — `scripts/backdoor_check.py` provides pattern scanning
- **No TLS bypasses** — No `verify=False` or certificate validation disabling
- **No fetch-and-execute** — No dynamic code download or execution patterns
- **JSON for serialization** — Checkpoint uses `json` (safe) instead of `pickle` (unsafe)
- **Comprehensive test suite** — 125 tests including dedicated exploit tests (`test_exploits.py`)
- **Security documentation** — `docs/SECURITY.md` and `SECURITY.md` vulnerability reporting policy

---

## Methodology Notes

This audit followed the Agentic Security Audit Checklist, applying all three tiers:

- **Tier 1 scans:** `grep` for plaintext secrets, git history analysis for deleted sensitive files, private key detection, Docker configuration review
- **Tier 2 scans:** Code injection patterns (`eval`/`exec`/`__import__`/`os.system`), insecure deserialization (`pickle`/`yaml.load`), TLS bypasses, path traversal analysis, network endpoint enumeration
- **Tier 3 scans:** Dependency pinning analysis, CI/CD pipeline review, fetch-and-execute patterns, container privilege escalation, audit logging assessment

**Tools used:** `grep`/`rg` pattern scanning, `git log` history analysis, `find` for sensitive file detection, manual code review of all 925 lines of production code and 304 lines of security tooling.

---

*Report generated: 2026-02-20*
*Methodology: Agentic Security Audit Checklist v1*
