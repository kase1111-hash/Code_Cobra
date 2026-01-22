# Support

Thank you for using Code Cobra! This document provides information on how to get help.

## Documentation

Before seeking support, please check our documentation:

- **[README](README.md)** - Overview and quick start guide
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API.md)** - Detailed API documentation
- **[FAQ](docs/FAQ.md)** - Frequently asked questions
- **[Security](docs/SECURITY.md)** - Security considerations

## Getting Help

### GitHub Issues

For bugs and feature requests, please use [GitHub Issues](https://github.com/kase1111-hash/Code_Cobra/issues):

- **[Bug Reports](https://github.com/kase1111-hash/Code_Cobra/issues/new?template=bug_report.md)** - Report unexpected behavior
- **[Feature Requests](https://github.com/kase1111-hash/Code_Cobra/issues/new?template=feature_request.md)** - Suggest new features

Before opening an issue, please:
1. Search existing issues to avoid duplicates
2. Check the [FAQ](docs/FAQ.md) for common questions
3. Include relevant information (version, OS, configuration)

### Security Issues

Do **NOT** open public issues for security vulnerabilities. Please see our [Security Policy](SECURITY.md) for responsible disclosure guidelines.

## Common Issues

### Ollama Connection Errors

```
ConnectionError: Failed to connect to Ollama API
```

**Solution**: Ensure Ollama is running:
```bash
ollama serve
```

### Model Not Found

```
ModelError: Model 'qwen2.5-coder:7b' not found
```

**Solution**: Pull the required model:
```bash
ollama pull qwen2.5-coder:7b
```

### Guide File Errors

```
ValueError: No valid steps found in guide file
```

**Solution**: Ensure your guide file follows the correct format:
```
Step 1: Description of first step
Step 2: Description of second step
```

### Memory Issues

For large workflows or models, you may need to:
- Use smaller models (e.g., 7B instead of 22B)
- Reduce `max_tokens` in configuration
- Process fewer steps at a time using `--checkpoint`

## Self-Help Resources

### Running Diagnostics

```bash
# Validate your setup
make dry-run

# Run tests
make test

# Check code quality
make analyze
```

### Checking Versions

```bash
# Python version
python --version

# Code Cobra version (check CHANGELOG.md)
head -20 CHANGELOG.md

# Ollama version
ollama --version

# Available models
ollama list
```

## Contributing

Want to help improve Code Cobra? See our [Contributing Guide](CONTRIBUTING.md) for:
- Code style guidelines
- Development setup
- Pull request process

## Stay Updated

Watch the repository on GitHub to receive notifications about:
- New releases
- Security updates
- Important announcements
