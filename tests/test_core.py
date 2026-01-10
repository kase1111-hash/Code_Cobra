#!/usr/bin/env python3
"""
Unit tests for Autonomous Coding Ensemble System core components.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonomous_ensemble import (
    Config,
    StepContext,
    OllamaRequest,
    GuideLoader,
    StateManager,
    Checkpoint,
    PipelineHooks,
)


class TestConfig(unittest.TestCase):
    """Tests for Config dataclass."""

    def test_default_values(self):
        """Test that Config has correct default values."""
        config = Config()
        self.assertEqual(config.ollama_api, "http://localhost:11434/api/generate")
        self.assertEqual(config.model_a, "qwen2.5-coder:7b")
        self.assertEqual(config.model_b, "deepseek-coder-v2:16b")
        self.assertEqual(config.model_c, "codestral:22b")
        self.assertEqual(config.temp_creative, 0.8)
        self.assertEqual(config.temp_analytical, 0.3)
        self.assertEqual(config.temp_adversarial, 0.7)
        self.assertEqual(config.max_tokens, 2000)
        self.assertEqual(config.max_iterations, 3)
        self.assertEqual(config.output_file, "final_output.txt")
        self.assertFalse(config.verbose)

    def test_from_json(self):
        """Test loading Config from JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "model_a": "custom-model:7b",
                "max_tokens": 4000,
                "verbose": True
            }, f)
            f.flush()

            config = Config.from_json(f.name)
            self.assertEqual(config.model_a, "custom-model:7b")
            self.assertEqual(config.max_tokens, 4000)
            self.assertTrue(config.verbose)
            # Defaults should remain
            self.assertEqual(config.model_b, "deepseek-coder-v2:16b")

        os.unlink(f.name)


class TestStepContext(unittest.TestCase):
    """Tests for StepContext dataclass."""

    def test_creation(self):
        """Test StepContext creation with required fields."""
        ctx = StepContext(
            step_number=1,
            step_description="Test step",
            spec="Test specification"
        )
        self.assertEqual(ctx.step_number, 1)
        self.assertEqual(ctx.step_description, "Test step")
        self.assertEqual(ctx.spec, "Test specification")
        self.assertEqual(ctx.previous_output, "")
        self.assertEqual(ctx.draft, "")
        self.assertEqual(ctx.corrected, "")
        self.assertEqual(ctx.secured, "")

    def test_with_previous_output(self):
        """Test StepContext with previous output."""
        ctx = StepContext(
            step_number=2,
            step_description="Second step",
            spec="Spec",
            previous_output="Previous content"
        )
        self.assertEqual(ctx.previous_output, "Previous content")


class TestOllamaRequest(unittest.TestCase):
    """Tests for OllamaRequest dataclass."""

    def test_to_dict(self):
        """Test conversion to API request dictionary."""
        request = OllamaRequest(
            model="test-model",
            prompt="Test prompt",
            temperature=0.5,
            max_tokens=1000
        )
        result = request.to_dict()

        self.assertEqual(result["model"], "test-model")
        self.assertEqual(result["prompt"], "Test prompt")
        self.assertEqual(result["options"]["temperature"], 0.5)
        self.assertFalse(result["stream"])
        self.assertEqual(result["max_tokens"], 1000)


class TestGuideLoader(unittest.TestCase):
    """Tests for GuideLoader class."""

    def test_load_valid_guide(self):
        """Test loading a valid guide file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Step 1: First step\n")
            f.write("Step 2: Second step\n")
            f.write("Step 3: Third step\n")
            f.flush()

            loader = GuideLoader(f.name)
            steps = loader.load()

            self.assertEqual(len(steps), 3)
            self.assertEqual(steps[0], "First step")
            self.assertEqual(steps[1], "Second step")
            self.assertEqual(steps[2], "Third step")

        os.unlink(f.name)

    def test_load_guide_with_gaps(self):
        """Test loading guide with non-sequential step numbers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Step 1: First\n")
            f.write("Step 5: Fifth\n")
            f.write("Step 3: Third\n")
            f.flush()

            loader = GuideLoader(f.name)
            steps = loader.load()

            # Should be sorted by step number
            self.assertEqual(len(steps), 3)
            self.assertEqual(steps[0], "First")
            self.assertEqual(steps[1], "Third")
            self.assertEqual(steps[2], "Fifth")

        os.unlink(f.name)

    def test_load_missing_file(self):
        """Test loading non-existent file raises FileNotFoundError."""
        loader = GuideLoader("/nonexistent/path/guide.txt")
        with self.assertRaises(FileNotFoundError):
            loader.load()

    def test_load_empty_guide(self):
        """Test loading empty guide raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not a valid step format\n")
            f.write("Neither is this\n")
            f.flush()

            loader = GuideLoader(f.name)
            with self.assertRaises(ValueError):
                loader.load()

        os.unlink(f.name)

    def test_case_insensitive_step_pattern(self):
        """Test that step pattern is case-insensitive."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("STEP 1: Uppercase\n")
            f.write("step 2: Lowercase\n")
            f.write("Step 3: Mixed\n")
            f.flush()

            loader = GuideLoader(f.name)
            steps = loader.load()

            self.assertEqual(len(steps), 3)

        os.unlink(f.name)


class TestStateManager(unittest.TestCase):
    """Tests for StateManager class."""

    def test_initial_state(self):
        """Test initial state values."""
        state = StateManager()
        self.assertEqual(state.cumulative_output, "")
        self.assertEqual(state.current_step_index, 0)
        self.assertEqual(state.step_outputs, [])

    def test_add_step_output(self):
        """Test adding step outputs."""
        state = StateManager()

        state.add_step_output("First output")
        self.assertEqual(state.current_step_index, 1)
        self.assertEqual(len(state.step_outputs), 1)
        self.assertIn("Step 1 Output", state.cumulative_output)
        self.assertIn("First output", state.cumulative_output)

        state.add_step_output("Second output")
        self.assertEqual(state.current_step_index, 2)
        self.assertEqual(len(state.step_outputs), 2)
        self.assertIn("Step 2 Output", state.cumulative_output)

    def test_get_context(self):
        """Test getting context returns cumulative output."""
        state = StateManager()
        state.add_step_output("Test output")

        context = state.get_context()
        self.assertEqual(context, state.cumulative_output)


class TestCheckpoint(unittest.TestCase):
    """Tests for Checkpoint class."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        checkpoint = Checkpoint(
            guide_file="test_guide.txt",
            spec="Test spec",
            completed_steps=5,
            cumulative_output="Output",
            step_outputs=["s1", "s2", "s3", "s4", "s5"],
            timestamp="2024-01-01T00:00:00"
        )
        result = checkpoint.to_dict()

        self.assertEqual(result["guide_file"], "test_guide.txt")
        self.assertEqual(result["spec"], "Test spec")
        self.assertEqual(result["completed_steps"], 5)
        self.assertEqual(result["cumulative_output"], "Output")
        self.assertEqual(len(result["step_outputs"]), 5)
        self.assertEqual(result["timestamp"], "2024-01-01T00:00:00")

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "guide_file": "guide.txt",
            "spec": "Spec",
            "completed_steps": 3,
            "cumulative_output": "Out",
            "step_outputs": ["a", "b", "c"],
            "timestamp": "2024-01-01T12:00:00"
        }
        checkpoint = Checkpoint.from_dict(data)

        self.assertEqual(checkpoint.guide_file, "guide.txt")
        self.assertEqual(checkpoint.completed_steps, 3)
        self.assertEqual(len(checkpoint.step_outputs), 3)

    def test_save_and_load(self):
        """Test saving and loading checkpoint."""
        checkpoint = Checkpoint(
            guide_file="test.txt",
            spec="Test",
            completed_steps=2,
            cumulative_output="Output",
            step_outputs=["one", "two"],
            timestamp="2024-01-01T00:00:00"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            checkpoint.save(f.name)

            loaded = Checkpoint.load(f.name)

            self.assertEqual(loaded.guide_file, checkpoint.guide_file)
            self.assertEqual(loaded.spec, checkpoint.spec)
            self.assertEqual(loaded.completed_steps, checkpoint.completed_steps)
            self.assertEqual(loaded.cumulative_output, checkpoint.cumulative_output)
            self.assertEqual(loaded.step_outputs, checkpoint.step_outputs)
            self.assertEqual(loaded.timestamp, checkpoint.timestamp)

        os.unlink(f.name)


class TestPipelineHooks(unittest.TestCase):
    """Tests for PipelineHooks dataclass."""

    def test_default_hooks_are_none(self):
        """Test that default hooks are None."""
        hooks = PipelineHooks()
        self.assertIsNone(hooks.post_draft)
        self.assertIsNone(hooks.post_correction)
        self.assertIsNone(hooks.post_security)

    def test_custom_hooks(self):
        """Test custom hook functions."""
        def custom_hook(text):
            return text.upper()

        hooks = PipelineHooks(post_draft=custom_hook)
        self.assertIsNotNone(hooks.post_draft)
        self.assertEqual(hooks.post_draft("test"), "TEST")


if __name__ == "__main__":
    unittest.main()
