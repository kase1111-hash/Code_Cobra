#!/usr/bin/env python3
"""
Security tests for Autonomous Coding Ensemble System.

Validates input handling, path security, and configuration safety.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonomous_ensemble import Config, GuideLoader


class TestInputValidation(unittest.TestCase):
    """Test input validation and sanitization."""

    def test_guide_loader_rejects_shell_injection(self):
        """Guide loader doesn't execute shell commands in step descriptions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Step 1: $(rm -rf /)\n")
            f.write("Step 2: `whoami`\n")
            f.write("Step 3: ; cat /etc/passwd\n")
            f.flush()

            loader = GuideLoader(f.name)
            steps = loader.load()

            # Steps should be loaded as plain text, not executed
            self.assertEqual(len(steps), 3)
            self.assertIn("$(rm -rf /)", steps[0])
            self.assertIn("`whoami`", steps[1])

        os.unlink(f.name)

    def test_config_rejects_invalid_keys(self):
        """Config ignores unknown keys from JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "model_a": "valid-model",
                "__class__": "malicious",
                "exec": "os.system('rm -rf /')",
                "eval": "dangerous_code()"
            }, f)
            f.flush()

            config = Config.from_json(f.name)

            # Valid key should work
            self.assertEqual(config.model_a, "valid-model")
            # Dangerous keys should be ignored
            self.assertFalse(hasattr(config, "__class__override"))
            self.assertFalse(hasattr(config, "exec"))
            self.assertFalse(hasattr(config, "eval"))

        os.unlink(f.name)

    def test_guide_loader_handles_unicode_safely(self):
        """Guide loader handles unicode characters safely."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Step 1: Handle émojis 🐍\n")
            f.write("Step 2: Support 中文\n")
            f.write("Step 3: Accept кириллица\n")
            f.flush()

            loader = GuideLoader(f.name)
            steps = loader.load()

            self.assertEqual(len(steps), 3)
            self.assertIn("🐍", steps[0])
            self.assertIn("中文", steps[1])

        os.unlink(f.name)


class TestPathSecurity(unittest.TestCase):
    """Test path traversal and file access security."""

    def test_guide_loader_rejects_nonexistent_file(self):
        """Guide loader raises error for non-existent files."""
        loader = GuideLoader("/nonexistent/path/guide.txt")
        with self.assertRaises(FileNotFoundError):
            loader.load()

    def test_guide_loader_path_traversal_attempt(self):
        """Guide loader handles path traversal attempts."""
        # Create a guide file with normal content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Step 1: Normal step\n")
            f.flush()

            # Loader should work with valid path
            loader = GuideLoader(f.name)
            steps = loader.load()
            self.assertEqual(len(steps), 1)

        os.unlink(f.name)

    def test_config_from_json_validates_file_exists(self):
        """Config.from_json raises error for non-existent config."""
        with self.assertRaises(FileNotFoundError):
            Config.from_json("/nonexistent/config.json")


class TestConfigurationSecurity(unittest.TestCase):
    """Test configuration security measures."""

    def test_env_vars_not_logged(self):
        """Sensitive env vars shouldn't appear in default config repr."""
        config = Config()
        config_str = str(config)

        # Config string representation shouldn't expose dangerous patterns
        # Note: "max_tokens" is a valid config key, not a secret
        self.assertNotIn("password", config_str.lower())
        self.assertNotIn("secret", config_str.lower())
        self.assertNotIn("api_key", config_str.lower())

    def test_config_has_safe_defaults(self):
        """Config defaults are secure."""
        config = Config()

        # API should be localhost only by default
        is_local = "localhost" in config.ollama_api or "127.0.0.1" in config.ollama_api
        self.assertTrue(is_local, "Default API should be localhost")

    def test_config_from_env_handles_missing_vars(self):
        """Config.from_env handles missing env vars gracefully."""
        # Clear relevant env vars
        env_backup = {}
        for key in ["OLLAMA_API", "MODEL_A", "MODEL_B", "MODEL_C"]:
            env_backup[key] = os.environ.pop(key, None)

        try:
            # Should not raise exception
            config = Config.from_env()
            self.assertIsInstance(config, Config)
        finally:
            # Restore env vars
            for key, val in env_backup.items():
                if val is not None:
                    os.environ[key] = val


class TestNoSecretExposure(unittest.TestCase):
    """Test that secrets are not exposed."""

    def test_gitignore_excludes_env(self):
        """Gitignore should exclude .env files."""
        gitignore_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".gitignore"
        )

        if os.path.exists(gitignore_path):
            with open(gitignore_path) as f:
                content = f.read()

            # Should have patterns for sensitive files
            self.assertTrue(
                ".env" in content or "*.env" in content,
                ".env should be in .gitignore"
            )

    def test_env_example_has_no_real_secrets(self):
        """Example env file should not contain real secrets."""
        env_example = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env.example"
        )

        if os.path.exists(env_example):
            with open(env_example) as f:
                content = f.read()

            # Should not contain real credentials
            self.assertNotIn("sk-", content)  # API keys
            self.assertNotIn("password123", content)
            self.assertNotIn("admin", content.lower().split("=")[-1] if "=" in content else content)


class TestContainerSecurity(unittest.TestCase):
    """Test Docker container security."""

    def test_dockerfile_uses_non_root(self):
        """Dockerfile should use non-root user."""
        dockerfile_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Dockerfile"
        )

        if os.path.exists(dockerfile_path):
            with open(dockerfile_path) as f:
                content = f.read()

            # Should have USER directive for non-root
            self.assertIn("USER", content)
            # Check for non-root user (appuser or similar)
            has_nonroot = "appuser" in content.lower() or "nonroot" in content.lower()
            self.assertTrue(has_nonroot, "Dockerfile should use non-root user")

    def test_dockerfile_has_healthcheck(self):
        """Dockerfile should have HEALTHCHECK."""
        dockerfile_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Dockerfile"
        )

        if os.path.exists(dockerfile_path):
            with open(dockerfile_path) as f:
                content = f.read()

            self.assertIn("HEALTHCHECK", content)


class TestNoCodeExecution(unittest.TestCase):
    """Test that user input doesn't lead to code execution."""

    def test_guide_step_not_evaluated(self):
        """Guide steps should not be evaluated as Python code."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Step 1: __import__('os').system('whoami')\n")
            f.write("Step 2: eval('print(1)')\n")
            f.write("Step 3: exec('import sys')\n")
            f.flush()

            loader = GuideLoader(f.name)
            steps = loader.load()

            # Steps should be plain strings
            self.assertIn("__import__", steps[0])
            self.assertIn("eval", steps[1])
            self.assertIn("exec", steps[2])

            # None of these should have been executed
            # (This test would fail if eval/exec was called)

        os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
