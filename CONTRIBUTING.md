# Contributing to Code Cobra

Thank you for your interest in contributing to Code Cobra! This document provides guidelines and conventions for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.

## Coding Conventions & Style Guide

### Python Style

We follow [PEP 8](https://peps.python.org/pep-0008/) with the following specifics:

#### Formatting
- **Line length**: Maximum 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings, single quotes for dict keys
- **Imports**: Group in order: stdlib, third-party, local

```python
# Standard library
import json
import os

# Third-party
import requests

# Local
from autonomous_ensemble import Config
```

#### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `GuideLoader`, `WorkflowEngine` |
| Functions | snake_case | `load_guide()`, `process_step()` |
| Variables | snake_case | `step_count`, `cumulative_output` |
| Constants | UPPER_SNAKE | `MAX_ITERATIONS`, `DEFAULT_PORT` |
| Private | _prefix | `_internal_method()` |

#### Type Hints
Always use type hints for function signatures:

```python
def process_step(self, step_desc: str, spec: str) -> str:
    """Process a single step through the pipeline."""
    ...
```

#### Docstrings
Use Google-style docstrings:

```python
def load(self, file_path: str) -> List[str]:
    """
    Load and parse the guide file.

    Args:
        file_path: Path to the guide file.

    Returns:
        Ordered list of step descriptions.

    Raises:
        FileNotFoundError: If guide file doesn't exist.
        ValueError: If no valid steps found.
    """
```

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(pipeline): add convergence detection for model iterations

fix(loader): handle empty guide files gracefully

docs(readme): add installation instructions
```

### Testing Standards

- Write tests for all new features
- Maintain >80% code coverage
- Use descriptive test names: `test_load_valid_guide_returns_ordered_steps`
- One assertion per test when possible

```python
class TestGuideLoader(unittest.TestCase):
    def test_load_valid_guide_returns_ordered_steps(self):
        """Verify that valid guide files return steps in order."""
        loader = GuideLoader("test_guide.txt")
        steps = loader.load()
        self.assertEqual(len(steps), 3)
```

### Error Handling

- Use specific exception types
- Provide helpful error messages
- Log errors with context

```python
if not os.path.exists(file_path):
    raise FileNotFoundError(
        f"Guide file not found: {file_path}\n"
        f"Available guides: {', '.join(available)}"
    )
```

## Development Workflow

### Setting Up

```bash
# Clone repository
git clone https://github.com/kase1111-hash/Code_Cobra.git
cd Code_Cobra

# Set up environment
./scripts/setup.sh --dev

# Activate virtual environment
source venv/bin/activate
```

### Before Submitting

1. Run tests: `make test`
2. Run linting: `make lint`
3. Run type check: `make typecheck`
4. Update documentation if needed
5. Add changelog entry for significant changes

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make changes following style guide
4. Write/update tests
5. Commit with conventional commit message
6. Push and create PR
7. Address review feedback

## Project Structure

```
Code_Cobra/
├── autonomous_ensemble.py  # Main application
├── tests/                  # Unit tests
│   ├── __init__.py
│   └── test_core.py
├── scripts/                # Utility scripts
│   └── setup.sh
├── .github/workflows/      # CI/CD
│   └── ci.yml
├── requirements.txt        # Production deps
├── requirements-dev.txt    # Development deps
├── Makefile               # Build automation
├── Dockerfile             # Container build
└── docker-compose.yml     # Container orchestration
```

## Questions?

Open an issue for questions or suggestions.
