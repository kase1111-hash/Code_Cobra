# Autonomous Coding Ensemble System - Makefile
# Build automation for development, testing, and deployment

.PHONY: all install test lint typecheck clean run dry-run help

# Default Python interpreter
PYTHON := python3
PIP := pip3

# Project settings
SRC := autonomous_ensemble.py
TESTS := tests/
GUIDE := coding_guide.txt

all: install lint typecheck test

# Install dependencies
install:
	$(PIP) install -r requirements.txt

# Install development dependencies
install-dev: install
	$(PIP) install mypy flake8 bandit

# Run all tests
test:
	$(PYTHON) -m unittest discover -s $(TESTS) -v

# Run linting with flake8
lint:
	@command -v flake8 >/dev/null 2>&1 && flake8 $(SRC) --max-line-length=100 --ignore=E501 || echo "flake8 not installed, skipping lint"

# Run type checking with mypy
typecheck:
	@command -v mypy >/dev/null 2>&1 && mypy $(SRC) --ignore-missing-imports || echo "mypy not installed, skipping type check"

# Run security scan with bandit
security:
	@command -v bandit >/dev/null 2>&1 && bandit -r $(SRC) -ll || echo "bandit not installed, skipping security scan"

# Run all static analysis
analyze: lint typecheck security

# Clean up generated files
clean:
	rm -rf __pycache__ tests/__pycache__ .mypy_cache
	rm -f *.pyc tests/*.pyc
	rm -f final_output.txt output_*.txt
	rm -f *.json

# Run dry-run validation
dry-run:
	$(PYTHON) $(SRC) --dry-run --guide $(GUIDE)

# Run with example spec (requires Ollama)
run:
	@echo "Usage: make run SPEC='your specification here'"
	@echo "Example: make run SPEC='Build a REST API for user management'"
ifdef SPEC
	$(PYTHON) $(SRC) --spec "$(SPEC)" --guide $(GUIDE) --verbose
endif

# Run guide chain dry-run
chain-dry-run:
	$(PYTHON) $(SRC) --dry-run --chain coding_guide.txt post_coding_guide.txt

# Show help
help:
	@echo "Autonomous Coding Ensemble System - Build Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  all          - Install, lint, typecheck, and test"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test         - Run unit tests"
	@echo "  lint         - Run flake8 linting"
	@echo "  typecheck    - Run mypy type checking"
	@echo "  security     - Run bandit security scan"
	@echo "  analyze      - Run all static analysis (lint, typecheck, security)"
	@echo "  clean        - Remove generated files"
	@echo "  dry-run      - Validate guide without running models"
	@echo "  chain-dry-run- Validate guide chain without running models"
	@echo "  run          - Run with spec (requires SPEC variable)"
	@echo "  help         - Show this help message"
