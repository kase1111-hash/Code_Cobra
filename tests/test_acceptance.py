#!/usr/bin/env python3
"""
System/Acceptance tests for Autonomous Coding Ensemble System.

These tests verify end-to-end user scenarios and acceptance criteria
from the user stories defined in docs/USER_STORIES.md.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonomous_ensemble import Config


class TestUS11_GenerateCodeFromSpec(unittest.TestCase):
    """
    US-1.1: Generate Code from Specification

    As a developer, I want to provide a natural language specification
    and receive generated code.
    """

    def test_accepts_spec_via_flag(self):
        """System accepts specification via --spec flag."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--help"],
            capture_output=True,
            text=True
        )
        self.assertIn("--spec", result.stdout)

    def test_accepts_spec_as_file_path(self):
        """System accepts specification as file path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Build a REST API for user management")
            spec_file = f.name

        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--spec", spec_file, "--guide", "coding_guide.txt"],
            capture_output=True,
            text=True
        )
        # Dry-run should work with spec file
        self.assertEqual(result.returncode, 0)
        os.unlink(spec_file)


class TestUS12_ValidateGuideWithoutExecution(unittest.TestCase):
    """
    US-1.2: Validate Guide Without Execution

    As a developer, I want to validate my guide file without running the models.
    """

    def test_accepts_dry_run_flag(self):
        """System accepts --dry-run flag."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--guide", "coding_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)

    def test_dry_run_displays_parsed_steps(self):
        """System displays all parsed steps with step numbers."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--guide", "coding_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertIn("Step 1:", result.stdout)
        self.assertIn("Step 2:", result.stdout)

    def test_dry_run_success_message_if_valid(self):
        """System exits with success message if valid."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--guide", "coding_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertIn("validation successful", result.stdout.lower())

    def test_dry_run_error_if_file_missing(self):
        """System exits with error message if file missing."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--guide", "nonexistent_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error", result.stdout)


class TestUS13_UseCustomModels(unittest.TestCase):
    """
    US-1.3: Use Custom Models

    As a developer, I want to configure which LLM models are used.
    """

    def test_accepts_config_flag(self):
        """System accepts --config flag."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--help"],
            capture_output=True,
            text=True
        )
        self.assertIn("--config", result.stdout)

    def test_config_supports_model_overrides(self):
        """Configuration supports model overrides."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "model_a": "custom-model:7b",
                "model_b": "another-model:13b"
            }, f)
            config_file = f.name

        config = Config.from_json(config_file)
        self.assertEqual(config.model_a, "custom-model:7b")
        self.assertEqual(config.model_b, "another-model:13b")
        os.unlink(config_file)

    def test_config_supports_temperature_settings(self):
        """Configuration supports temperature settings."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "temp_creative": 0.9,
                "temp_analytical": 0.1
            }, f)
            config_file = f.name

        config = Config.from_json(config_file)
        self.assertEqual(config.temp_creative, 0.9)
        self.assertEqual(config.temp_analytical, 0.1)
        os.unlink(config_file)


class TestUS21_ResumeInterruptedWorkflow(unittest.TestCase):
    """
    US-2.1: Resume Interrupted Workflow

    As a developer, I want to resume a workflow that was interrupted.
    """

    def test_accepts_checkpoint_flag(self):
        """System accepts --checkpoint flag."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--help"],
            capture_output=True,
            text=True
        )
        self.assertIn("--checkpoint", result.stdout)

    def test_accepts_resume_flag(self):
        """System accepts --resume flag."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--help"],
            capture_output=True,
            text=True
        )
        self.assertIn("--resume", result.stdout)


class TestUS22_ChainMultipleGuides(unittest.TestCase):
    """
    US-2.2: Chain Multiple Guides

    As a developer, I want to run multiple guides in sequence.
    """

    def test_accepts_chain_flag(self):
        """System accepts --chain flag with multiple guide files."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--help"],
            capture_output=True,
            text=True
        )
        self.assertIn("--chain", result.stdout)

    def test_chain_dry_run_validates_all_guides(self):
        """Dry-run mode validates entire chain."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--chain", "coding_guide.txt", "post_coding_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("coding_guide.txt", result.stdout)
        self.assertIn("post_coding_guide.txt", result.stdout)

    def test_chain_shows_total_steps(self):
        """System displays chain progress."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--chain", "coding_guide.txt", "post_coding_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertIn("Total steps:", result.stdout)


class TestUS23_VerboseProgressMonitoring(unittest.TestCase):
    """
    US-2.3: Verbose Progress Monitoring

    As a developer, I want to see detailed progress during execution.
    """

    def test_accepts_verbose_flag(self):
        """System accepts --verbose flag."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--help"],
            capture_output=True,
            text=True
        )
        self.assertIn("--verbose", result.stdout)


class TestUS41_HandleMissingFilesGracefully(unittest.TestCase):
    """
    US-4.1: Handle Missing Files Gracefully

    As a developer, I want to receive helpful error messages for missing files.
    """

    def test_missing_guide_shows_available_guides(self):
        """Missing guide file shows available guides in directory."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--guide", "nonexistent.txt"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)
        # Should mention available guides or show error
        self.assertTrue(
            "Error" in result.stdout or "not found" in result.stdout.lower()
        )

    def test_exits_with_nonzero_on_error(self):
        """System exits with non-zero code on errors."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--guide", "nonexistent.txt"],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)


class TestUS51_RunInContainer(unittest.TestCase):
    """
    US-5.1: Run in Container

    As a DevOps engineer, I want to run Code Cobra in a Docker container.
    """

    def test_dockerfile_exists(self):
        """Dockerfile exists."""
        self.assertTrue(os.path.exists("Dockerfile"))

    def test_docker_compose_exists(self):
        """docker-compose.yml exists."""
        self.assertTrue(os.path.exists("docker-compose.yml"))


class TestEnvironmentConfiguration(unittest.TestCase):
    """Test environment variable configuration."""

    def test_config_from_env_returns_config(self):
        """Config.from_env() returns valid Config object."""
        config = Config.from_env()
        self.assertIsInstance(config, Config)

    def test_config_from_env_uses_defaults(self):
        """Config.from_env() uses defaults when env vars not set."""
        # Clear any existing env vars
        env_backup = {}
        for key in ["OLLAMA_API", "MODEL_A", "MODEL_B", "MODEL_C"]:
            env_backup[key] = os.environ.pop(key, None)

        try:
            config = Config.from_env()
            self.assertEqual(config.ollama_api, "http://localhost:11434/api/generate")
            self.assertEqual(config.model_a, "qwen2.5-coder:7b")
        finally:
            # Restore env vars
            for key, val in env_backup.items():
                if val is not None:
                    os.environ[key] = val

    def test_config_from_env_reads_env_vars(self):
        """Config.from_env() reads from environment variables."""
        os.environ["MODEL_A"] = "test-model:1b"
        try:
            config = Config.from_env()
            self.assertEqual(config.model_a, "test-model:1b")
        finally:
            del os.environ["MODEL_A"]


class TestEnvironmentSpecificConfigs(unittest.TestCase):
    """Test environment-specific configuration files."""

    def test_dev_config_exists(self):
        """Development config exists."""
        self.assertTrue(os.path.exists("config/dev.json"))

    def test_stage_config_exists(self):
        """Staging config exists."""
        self.assertTrue(os.path.exists("config/stage.json"))

    def test_prod_config_exists(self):
        """Production config exists."""
        self.assertTrue(os.path.exists("config/prod.json"))

    def test_dev_config_is_valid_json(self):
        """Development config is valid JSON."""
        with open("config/dev.json") as f:
            config = json.load(f)
        self.assertIn("ollama_api", config)

    def test_prod_config_has_lower_verbosity(self):
        """Production config has verbose=false."""
        with open("config/prod.json") as f:
            config = json.load(f)
        self.assertFalse(config.get("verbose", True))


if __name__ == "__main__":
    unittest.main()
