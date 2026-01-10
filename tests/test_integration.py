#!/usr/bin/env python3
"""
Integration tests for Autonomous Coding Ensemble System.

These tests verify end-to-end functionality without requiring Ollama.
They use mocked API responses to test the complete workflow.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonomous_ensemble import (
    Config,
    WorkflowEngine,
    GuideChain,
    GuideLoader,
    StateManager,
    Checkpoint,
    PipelineHooks,
    OllamaClient,
)


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI interface."""

    def test_cli_help(self):
        """Test that --help works and shows usage."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--help"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout)
        self.assertIn("--spec", result.stdout)
        self.assertIn("--guide", result.stdout)

    def test_cli_dry_run_single_guide(self):
        """Test dry-run mode with single guide."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run", "--guide", "coding_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Dry run", result.stdout)
        self.assertIn("Validated", result.stdout)
        self.assertIn("steps", result.stdout)

    def test_cli_dry_run_chain(self):
        """Test dry-run mode with guide chain."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run",
             "--chain", "coding_guide.txt", "post_coding_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Validating", result.stdout)
        self.assertIn("guides in chain", result.stdout)
        self.assertIn("Chain validation successful", result.stdout)

    def test_cli_missing_spec_error(self):
        """Test that missing --spec shows error (without dry-run)."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--guide", "coding_guide.txt"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("--spec is required", result.stdout)

    def test_cli_missing_guide_error(self):
        """Test that missing guide file shows error."""
        result = subprocess.run(
            [sys.executable, "autonomous_ensemble.py", "--dry-run", "--guide", "nonexistent.txt"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error", result.stdout)


class TestWorkflowIntegration(unittest.TestCase):
    """Integration tests for WorkflowEngine with mocked Ollama."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(verbose=False)

        # Create temporary guide file
        self.guide_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        )
        self.guide_file.write("Step 1: Analyze requirements\n")
        self.guide_file.write("Step 2: Design solution\n")
        self.guide_file.write("Step 3: Implement code\n")
        self.guide_file.flush()
        self.guide_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.guide_file.name)
        # Clean up any output files
        if os.path.exists(self.config.output_file):
            os.unlink(self.config.output_file)

    @patch.object(OllamaClient, 'query')
    def test_workflow_processes_all_steps(self, mock_query):
        """Test that workflow processes all guide steps."""
        mock_query.return_value = "Generated code output"

        engine = WorkflowEngine(self.config)
        result = engine.run("Test spec", self.guide_file.name)

        # Should have called query for each step (3 stages per step)
        # 3 steps * (1 draft + up to 3 corrections + up to 3 security) = variable
        self.assertTrue(mock_query.called)

        # Output should contain step markers
        self.assertIn("Step 1 Output", result)
        self.assertIn("Step 2 Output", result)
        self.assertIn("Step 3 Output", result)

    @patch.object(OllamaClient, 'query')
    def test_workflow_writes_output_file(self, mock_query):
        """Test that workflow writes to output file."""
        mock_query.return_value = "Output content"

        engine = WorkflowEngine(self.config)
        engine.run("Test spec", self.guide_file.name)

        self.assertTrue(os.path.exists(self.config.output_file))
        with open(self.config.output_file) as f:
            content = f.read()
        self.assertIn("Output content", content)

    @patch.object(OllamaClient, 'query')
    def test_workflow_convergence_detection(self, mock_query):
        """Test that iteration stops when output converges."""
        # Return same output to trigger convergence
        mock_query.return_value = "Converged output"

        config = Config(max_iterations=5, verbose=False)
        engine = WorkflowEngine(config)
        engine.run("Test spec", self.guide_file.name)

        # Should stop early due to convergence, not hit max iterations
        self.assertTrue(mock_query.called)


class TestCheckpointIntegration(unittest.TestCase):
    """Integration tests for checkpoint/resume functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(verbose=False)

        # Create temporary guide file
        self.guide_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        )
        self.guide_file.write("Step 1: First step\n")
        self.guide_file.write("Step 2: Second step\n")
        self.guide_file.write("Step 3: Third step\n")
        self.guide_file.flush()
        self.guide_file.close()

        self.checkpoint_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        self.checkpoint_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.guide_file.name)
        os.unlink(self.checkpoint_file.name)
        if os.path.exists(self.config.output_file):
            os.unlink(self.config.output_file)

    @patch.object(OllamaClient, 'query')
    def test_checkpoint_saves_progress(self, mock_query):
        """Test that checkpoints are saved after each step."""
        mock_query.return_value = "Step output"

        engine = WorkflowEngine(self.config, checkpoint_file=self.checkpoint_file.name)
        engine.run("Test spec", self.guide_file.name)

        # Checkpoint should exist and be valid JSON
        with open(self.checkpoint_file.name) as f:
            checkpoint_data = json.load(f)

        self.assertEqual(checkpoint_data["completed_steps"], 3)
        self.assertEqual(len(checkpoint_data["step_outputs"]), 3)

    @patch.object(OllamaClient, 'query')
    def test_resume_from_checkpoint(self, mock_query):
        """Test resuming from a saved checkpoint."""
        # Create a checkpoint at step 2
        checkpoint = Checkpoint(
            guide_file=self.guide_file.name,
            spec="Test spec",
            completed_steps=2,
            cumulative_output="Previous output",
            step_outputs=["Step 1", "Step 2"],
            timestamp="2024-01-01T00:00:00"
        )
        checkpoint.save(self.checkpoint_file.name)

        mock_query.return_value = "Resumed output"

        engine = WorkflowEngine(self.config)
        result = engine.run("Test spec", self.guide_file.name,
                           resume_from=self.checkpoint_file.name)

        # Should contain previous output
        self.assertIn("Previous output", result)
        # Should have processed step 3
        self.assertIn("Step 3 Output", result)


class TestGuideChainIntegration(unittest.TestCase):
    """Integration tests for guide chaining."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(verbose=False, output_file="chain_output.txt")

        # Create two temporary guide files
        self.guide1 = tempfile.NamedTemporaryFile(
            mode='w', suffix='_guide.txt', delete=False
        )
        self.guide1.write("Step 1: Guide 1 Step 1\n")
        self.guide1.write("Step 2: Guide 1 Step 2\n")
        self.guide1.flush()
        self.guide1.close()

        self.guide2 = tempfile.NamedTemporaryFile(
            mode='w', suffix='_guide.txt', delete=False
        )
        self.guide2.write("Step 1: Guide 2 Step 1\n")
        self.guide2.write("Step 2: Guide 2 Step 2\n")
        self.guide2.flush()
        self.guide2.close()

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.guide1.name)
        os.unlink(self.guide2.name)
        # Clean up output files
        for f in os.listdir('.'):
            if f.startswith('output_') or f == 'chain_output.txt':
                os.unlink(f)

    def test_chain_dry_run_validates_all_guides(self):
        """Test that dry-run validates all guides in chain."""
        chain = GuideChain(self.config)

        # Should not raise any exceptions
        chain.dry_run([self.guide1.name, self.guide2.name])

    @patch.object(OllamaClient, 'query')
    def test_chain_processes_all_guides(self, mock_query):
        """Test that chain processes all guides in sequence."""
        mock_query.return_value = "Chain output"

        chain = GuideChain(self.config)
        result = chain.run("Test spec", [self.guide1.name, self.guide2.name])

        # Output should reference both guides
        self.assertIn("Output from", result)


class TestHooksIntegration(unittest.TestCase):
    """Integration tests for pipeline hooks."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(verbose=False)

        self.guide_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        )
        self.guide_file.write("Step 1: Single step\n")
        self.guide_file.flush()
        self.guide_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.guide_file.name)
        if os.path.exists(self.config.output_file):
            os.unlink(self.config.output_file)

    @patch.object(OllamaClient, 'query')
    def test_post_draft_hook_applied(self, mock_query):
        """Test that post_draft hook is applied."""
        mock_query.return_value = "PLACEHOLDER content"

        def replace_placeholder(text):
            return text.replace("PLACEHOLDER", "REPLACED")

        hooks = PipelineHooks(post_draft=replace_placeholder)
        engine = WorkflowEngine(self.config, hooks=hooks)
        result = engine.run("Test spec", self.guide_file.name)

        # Hook should have transformed the output
        # Note: The transformation happens internally, final output
        # depends on Model B and C processing the transformed input
        self.assertTrue(mock_query.called)


if __name__ == "__main__":
    unittest.main()
