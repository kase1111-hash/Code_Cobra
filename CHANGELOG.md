# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-01-10

### Added
- Initial release of Autonomous Coding Ensemble System
- Multi-agent AI coding pipeline with three specialized models:
  - Model A (Creative): Generates initial drafts at high temperature (0.8)
  - Model B (Analytical): Error correction with iterative refinement (0.3)
  - Model C (Adversarial): Security hardening and vulnerability scanning (0.7)
- Guide Loader for parsing step-by-step instruction files
- Configuration system with JSON file support
- State Manager for tracking workflow progress
- Checkpoint/Resume functionality for long-running workflows
- Guide Chaining for sequential execution of multiple guides
- Custom Model Hooks for pipeline extensibility
- CLI interface with comprehensive options:
  - `--spec`: Project specification input
  - `--guide`: Guide file selection
  - `--output`: Output file configuration
  - `--config`: JSON configuration override
  - `--verbose`: Detailed logging mode
  - `--dry-run`: Validation without model execution
  - `--checkpoint`: Progress checkpointing
  - `--resume`: Resume from checkpoint
  - `--chain`: Multi-guide chaining
  - `--checkpoint-dir`: Chain checkpoint directory
- Example guide files:
  - `coding_guide.txt`: 40-step code generation workflow
  - `post_coding_guide.txt`: 40-step security hardening workflow
- Comprehensive unit test suite (18 tests)
- MIT License

### Technical Details
- Python 3.8+ compatibility
- Ollama API integration for local LLM inference
- Retry logic with exponential backoff for API resilience
- Convergence detection for iterative model stages
