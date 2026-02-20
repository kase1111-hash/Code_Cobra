# Security Documentation

## Overview

Code Cobra is designed with security as a priority. This document outlines security considerations, implemented safeguards, and best practices.

## Security Model

### Local-Only Processing

Code Cobra operates entirely locally:
- All LLM inference happens via local Ollama server
- No external API calls to cloud services
- Specification and output data never leaves your machine
- Full data sovereignty maintained

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                     TRUSTED ZONE (Local)                        │
│  ┌─────────────┐           ┌─────────────┐                     │
│  │ Code Cobra  │◄─────────▶│   Ollama    │                     │
│  │ Application │  HTTP     │   Server    │                     │
│  └─────────────┘ localhost └─────────────┘                     │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐                                               │
│  │   Output    │ ◄── Review before production use              │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Implemented Security Measures

### 1. Input Validation

**Guide File Validation**
- Regex-based step parsing prevents injection
- File existence checks before processing
- Step format validation (Step N: description)

**Specification Handling**
- Specs can be strings or file paths
- File path resolution is validated
- No shell expansion or command execution

### 2. Configuration Security

**Environment Variables**
- Sensitive configuration via .env files
- .env excluded from version control (.gitignore)
- No secrets in source code or logs

**Configuration Files**
- JSON-only configuration format
- No code execution in config loading
- Strict key validation

### 3. Container Security

**Dockerfile Best Practices**
- Non-root user (appuser)
- Minimal base image (python:slim)
- No unnecessary packages
- Health checks enabled

**Runtime Isolation**
- Container runs without elevated privileges
- Network limited to Ollama communication
- Volume mounts are explicit and controlled

### 4. Output Security

**Generated Code Review**
- All output should be reviewed before use
- Model C (Adversary) performs security scanning
- No automatic code execution

**Logging Safety**
- No secrets in log output
- Structured logging for audit trails
- Log file permissions controlled

## Security Checklist

### Pre-Deployment
- [ ] Review .env configuration
- [ ] Verify Ollama is on localhost only
- [ ] Check file permissions on output directory
- [ ] Ensure Docker runs as non-root

### During Development
- [ ] Never commit .env files
- [ ] Review Model C security suggestions
- [ ] Validate all external inputs
- [ ] Use type hints for safety

### For Production Output
- [ ] Run static analysis on generated code
- [ ] Perform security code review
- [ ] Test for common vulnerabilities
- [ ] Validate in staging environment

## Component Access Model

Each module has defined access expectations. Path validation enforces these at
runtime; the table below documents the intended boundaries.

| Component | File System Access | Network Access |
|-----------|--------------------|----------------|
| `GuideLoader` | Reads guide files within working directory | None |
| `WorkflowEngine` | Reads spec files within working directory; writes output and checkpoint files within working directory | None |
| `OllamaClient` | None | HTTP POST to configured `ollama_api` URL (default: `localhost:11434`) |
| `Checkpoint` | Reads/writes checkpoint JSON + HMAC files within working directory | None |
| `GuideChain` | Reads guides; writes per-guide outputs and checkpoints within working directory | None |
| `AuditLogger` | Appends to `audit.jsonl` in working directory | None |
| `OutputScanner` | None (in-memory scan only) | None |

### Checkpoint Integrity

Checkpoint files are protected by HMAC-SHA256. On save, a digest is written to
`<checkpoint>.hmac`. On load, if the HMAC file exists, the digest is verified
before deserialization. The HMAC key is derived from the `CHECKPOINT_SECRET`
environment variable (default: `"code-cobra-local"`).

### Prompt Injection Mitigation

User-supplied specification content is wrapped in `<user_specification>` delimiter
tags to separate it from system instructions. A lightweight heuristic scanner
checks spec content for common prompt injection patterns and logs warnings.

## Potential Attack Vectors

### Mitigated Risks

| Risk | Mitigation |
|------|------------|
| Command Injection | No shell execution of user input |
| Path Traversal | File paths validated, no arbitrary access |
| Secret Exposure | .env files excluded, no secrets in logs |
| Container Escape | Non-root user, minimal privileges |
| Prompt Injection | Model C adversarial review |

### Residual Risks

| Risk | Recommendation |
|------|----------------|
| Malicious Guide Files | Only use trusted guide files |
| LLM Output Quality | Always review generated code |
| Ollama Vulnerabilities | Keep Ollama updated |
| Local Access | Protect local machine access |

## Vulnerability Reporting

To report security vulnerabilities:
1. Do NOT open public issues
2. Email security concerns privately
3. Include reproduction steps
4. Allow time for patching before disclosure

## Security Updates

Security patches are prioritized and released as:
- Patch versions for fixes (v1.0.x)
- Minor versions for improvements (v1.x.0)

Check CHANGELOG.md for security-related updates.
