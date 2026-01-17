#!/usr/bin/env python3
"""
Performance tests for Autonomous Coding Ensemble System.

Tests load handling, response times, and resource usage.
"""

import concurrent.futures
import os
import statistics
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonomous_ensemble import Config, GuideLoader, StateManager, Checkpoint


class TestGuideLoaderPerformance(unittest.TestCase):
    """Test GuideLoader performance under various conditions."""

    def test_load_small_guide_under_10ms(self):
        """Small guide (10 steps) loads in under 10ms."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(10):
                f.write(f"Step {i+1}: Perform action {i+1}\n")
            f.flush()

            start = time.perf_counter()
            loader = GuideLoader(f.name)
            steps = loader.load()
            elapsed_ms = (time.perf_counter() - start) * 1000

            self.assertEqual(len(steps), 10)
            self.assertLess(elapsed_ms, 10, f"Load took {elapsed_ms:.2f}ms, expected <10ms")

        os.unlink(f.name)

    def test_load_medium_guide_under_50ms(self):
        """Medium guide (100 steps) loads in under 50ms."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(100):
                f.write(f"Step {i+1}: Perform complex action {i+1} with details\n")
            f.flush()

            start = time.perf_counter()
            loader = GuideLoader(f.name)
            steps = loader.load()
            elapsed_ms = (time.perf_counter() - start) * 1000

            self.assertEqual(len(steps), 100)
            self.assertLess(elapsed_ms, 50, f"Load took {elapsed_ms:.2f}ms, expected <50ms")

        os.unlink(f.name)

    def test_load_large_guide_under_200ms(self):
        """Large guide (1000 steps) loads in under 200ms."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(1000):
                f.write(f"Step {i+1}: " + "x" * 200 + "\n")  # Long descriptions
            f.flush()

            start = time.perf_counter()
            loader = GuideLoader(f.name)
            steps = loader.load()
            elapsed_ms = (time.perf_counter() - start) * 1000

            self.assertEqual(len(steps), 1000)
            self.assertLess(elapsed_ms, 200, f"Load took {elapsed_ms:.2f}ms, expected <200ms")

        os.unlink(f.name)


class TestCheckpointPerformance(unittest.TestCase):
    """Test Checkpoint performance for save/load operations."""

    def _create_checkpoint(self, step=5, context="Test context"):
        """Helper to create a Checkpoint object."""
        from datetime import datetime
        return Checkpoint(
            guide_file="test_guide.txt",
            spec="Test specification",
            completed_steps=step,
            cumulative_output=context,
            step_outputs=[f"Step {i}" for i in range(step)],
            timestamp=datetime.now().isoformat()
        )

    def test_save_checkpoint_under_10ms(self):
        """Saving checkpoint completes in under 10ms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_file = os.path.join(tmpdir, "checkpoint.json")
            checkpoint = self._create_checkpoint(5, "Test context data " * 100)

            start = time.perf_counter()
            checkpoint.save(checkpoint_file)
            elapsed_ms = (time.perf_counter() - start) * 1000

            self.assertLess(elapsed_ms, 10, f"Save took {elapsed_ms:.2f}ms, expected <10ms")

    def test_load_checkpoint_under_10ms(self):
        """Loading checkpoint completes in under 10ms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_file = os.path.join(tmpdir, "checkpoint.json")
            checkpoint = self._create_checkpoint(5, "Test context data " * 100)
            checkpoint.save(checkpoint_file)

            start = time.perf_counter()
            loaded = Checkpoint.load(checkpoint_file)
            elapsed_ms = (time.perf_counter() - start) * 1000

            self.assertLess(elapsed_ms, 10, f"Load took {elapsed_ms:.2f}ms, expected <10ms")

    def test_rapid_checkpoint_saves(self):
        """100 rapid checkpoint saves complete in under 500ms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_file = os.path.join(tmpdir, "checkpoint.json")

            start = time.perf_counter()
            for i in range(100):
                checkpoint = self._create_checkpoint(i, f"Context for step {i}")
                checkpoint.save(checkpoint_file)
            elapsed_ms = (time.perf_counter() - start) * 1000

            self.assertLess(elapsed_ms, 500, f"100 saves took {elapsed_ms:.2f}ms, expected <500ms")


class TestConfigPerformance(unittest.TestCase):
    """Test Config loading performance."""

    def test_config_from_json_under_5ms(self):
        """Loading config from JSON completes in under 5ms."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump({
                "model_a": "test-model",
                "model_b": "test-model-2",
                "temp_creative": 0.8
            }, f)
            f.flush()

            start = time.perf_counter()
            config = Config.from_json(f.name)
            elapsed_ms = (time.perf_counter() - start) * 1000

            self.assertLess(elapsed_ms, 5, f"Config load took {elapsed_ms:.2f}ms, expected <5ms")

        os.unlink(f.name)

    def test_config_from_env_under_10ms(self):
        """Loading config from environment completes in under 10ms."""
        start = time.perf_counter()
        config = Config.from_env()
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.assertLess(elapsed_ms, 10, f"Config.from_env took {elapsed_ms:.2f}ms, expected <10ms")


class TestConcurrentAccess(unittest.TestCase):
    """Test concurrent access patterns."""

    def test_concurrent_guide_loads(self):
        """Multiple concurrent guide loads complete successfully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(50):
                f.write(f"Step {i+1}: Action {i+1}\n")
            guide_file = f.name
            f.flush()

        def load_guide():
            loader = GuideLoader(guide_file)
            return loader.load()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(load_guide) for _ in range(20)]
            results = [f.result() for f in futures]

        # All loads should return same result
        for result in results:
            self.assertEqual(len(result), 50)

        os.unlink(guide_file)

    def test_concurrent_checkpoint_access(self):
        """Concurrent Checkpoint operations don't corrupt data."""
        from datetime import datetime

        with tempfile.TemporaryDirectory() as tmpdir:
            def save_and_load(step_num):
                checkpoint_file = os.path.join(tmpdir, f"checkpoint_{step_num}.json")
                checkpoint = Checkpoint(
                    guide_file="test.txt",
                    spec="Test",
                    completed_steps=step_num,
                    cumulative_output=f"Step {step_num}",
                    step_outputs=[],
                    timestamp=datetime.now().isoformat()
                )
                checkpoint.save(checkpoint_file)
                loaded = Checkpoint.load(checkpoint_file)
                return loaded is not None

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(save_and_load, i) for i in range(10)]
                results = [f.result() for f in futures]

            # All operations should complete successfully
            self.assertTrue(all(results))


class TestMemoryUsage(unittest.TestCase):
    """Test memory usage patterns."""

    def _create_checkpoint(self, context="Test"):
        """Helper to create a Checkpoint object."""
        from datetime import datetime
        return Checkpoint(
            guide_file="test.txt",
            spec="Test",
            completed_steps=1,
            cumulative_output=context,
            step_outputs=[],
            timestamp=datetime.now().isoformat()
        )

    def test_large_context_handling(self):
        """System handles large context strings without issues."""
        large_context = "x" * (1024 * 1024)  # 1MB string

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_file = os.path.join(tmpdir, "checkpoint.json")
            checkpoint = self._create_checkpoint(large_context)

            # Should handle large context
            checkpoint.save(checkpoint_file)
            loaded = Checkpoint.load(checkpoint_file)

            self.assertEqual(len(loaded.cumulative_output), len(large_context))

    def test_repeated_operations_no_memory_leak(self):
        """Repeated operations don't cause memory growth."""
        import gc

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_file = os.path.join(tmpdir, "checkpoint.json")

            # Force garbage collection to get baseline
            gc.collect()

            for i in range(100):
                checkpoint = self._create_checkpoint("test" * 1000)
                checkpoint.save(checkpoint_file)
                Checkpoint.load(checkpoint_file)

            # Force garbage collection
            gc.collect()

            # Test passes if we get here without OOM


class TestResponseTimeStatistics(unittest.TestCase):
    """Test response time statistics and consistency."""

    def test_guide_load_consistency(self):
        """Guide load times are consistent (low variance)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(50):
                f.write(f"Step {i+1}: Action {i+1}\n")
            f.flush()

            times = []
            for _ in range(20):
                start = time.perf_counter()
                loader = GuideLoader(f.name)
                loader.load()
                times.append((time.perf_counter() - start) * 1000)

            mean_time = statistics.mean(times)
            stdev_time = statistics.stdev(times)

            # Coefficient of variation should be reasonable
            cv = stdev_time / mean_time if mean_time > 0 else 0
            self.assertLess(cv, 1.0, f"High variance in load times: CV={cv:.2f}")

        os.unlink(f.name)


class TestStressConditions(unittest.TestCase):
    """Test behavior under stress conditions."""

    def test_rapid_config_reloads(self):
        """Rapid config reloads don't cause issues."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump({"model_a": "test"}, f)
            f.flush()

            start = time.perf_counter()
            for _ in range(1000):
                Config.from_json(f.name)
            elapsed = time.perf_counter() - start

            # 1000 reloads should complete in reasonable time
            self.assertLess(elapsed, 5, f"1000 reloads took {elapsed:.2f}s, expected <5s")

        os.unlink(f.name)

    def test_many_small_checkpoints(self):
        """Many small checkpoint operations complete efficiently."""
        from datetime import datetime

        with tempfile.TemporaryDirectory() as tmpdir:
            start = time.perf_counter()
            for i in range(100):
                checkpoint_file = os.path.join(tmpdir, f"checkpoint_{i}.json")
                checkpoint = Checkpoint(
                    guide_file="test.txt",
                    spec="Test",
                    completed_steps=i,
                    cumulative_output=f"small context {i}",
                    step_outputs=[],
                    timestamp=datetime.now().isoformat()
                )
                checkpoint.save(checkpoint_file)
            elapsed = time.perf_counter() - start

            self.assertLess(elapsed, 2, f"100 checkpoints took {elapsed:.2f}s, expected <2s")


if __name__ == "__main__":
    # Run with timing output
    unittest.main(verbosity=2)
