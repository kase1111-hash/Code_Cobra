# Security Policy

## Supported Versions

The following versions of Code Cobra are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue in Code Cobra, please follow these guidelines:

### Do NOT

- Open a public GitHub issue for security vulnerabilities
- Disclose the vulnerability publicly before it has been addressed
- Exploit the vulnerability beyond what is necessary for verification

### Do

1. **Email your report privately** to the maintainers
2. **Include detailed information:**
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Any suggested fixes (optional)
3. **Allow reasonable time** for the maintainers to address the issue before public disclosure (typically 90 days)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your report within 48 hours
- **Assessment**: We will investigate and assess the severity within 7 days
- **Updates**: We will keep you informed of our progress
- **Resolution**: Security patches are prioritized and released as soon as possible
- **Credit**: With your permission, we will credit you in the security advisory

## Security Measures

Code Cobra implements several security measures by design:

- **Local-only processing**: All LLM inference happens via local Ollama server
- **No external API calls**: Your data never leaves your machine
- **Non-root container execution**: Docker runs as unprivileged user
- **Input validation**: Guide files and specifications are validated before processing
- **Adversarial security scanning**: Model C performs security vulnerability analysis

For detailed security documentation, see [docs/SECURITY.md](docs/SECURITY.md).

## Security Updates

Security-related updates are documented in [CHANGELOG.md](CHANGELOG.md) and released as:

- **Patch versions** (v1.0.x) for security fixes
- **Minor versions** (v1.x.0) for security improvements
