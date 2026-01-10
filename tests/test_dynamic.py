#!/usr/bin/env python3
"""
Dynamic analysis and fuzzing tests for Autonomous Coding Ensemble System.

Tests runtime behavior, fuzz inputs, and monitors for anomalies.
"""

import json
import os
import random
import string
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonomous_ensemble import Config, GuideLoader, Checkpoint, StateManager


class FuzzGenerator:
    """Generates fuzz test data."""

    @staticmethod
    def random_string(length: int = 100) -> str:
        """Generate random string of specified length."""
        chars = string.printable
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def random_unicode(length: int = 50) -> str:
        """Generate random unicode string."""
        ranges = [
            (0x0020, 0x007F),  # Basic Latin
            (0x00A0, 0x00FF),  # Latin-1 Supplement
            (0x0100, 0x017F),  # Latin Extended-A
            (0x0400, 0x04FF),  # Cyrillic
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            (0x1F600, 0x1F64F),  # Emoticons
        ]
        chars = []
        for _ in range(length):
            start, end = random.choice(ranges)
            try:
                chars.append(chr(random.randint(start, end)))
            except (ValueError, OverflowError):
                chars.append('?')
        return ''.join(chars)

    @staticmethod
    def random_bytes(length: int = 100) -> bytes:
        """Generate random bytes."""
        return bytes(random.randint(0, 255) for _ in range(length))

    @staticmethod
    def mutation_fuzz(base: str, mutations: int = 5) -> str:
        """Apply random mutations to base string."""
        result = list(base)
        for _ in range(mutations):
            if not result:
                break
            pos = random.randint(0, len(result) - 1)
            mutation = random.choice(['insert', 'delete', 'replace'])
            if mutation == 'insert':
                result.insert(pos, random.choice(string.printable))
            elif mutation == 'delete':
                result.pop(pos)
            else:
                result[pos] = random.choice(string.printable)
        return ''.join(result)


class TestGuideLoaderFuzzing(unittest.TestCase):
    """Fuzz testing for GuideLoader."""

    def test_random_content_no_crash(self):
        """GuideLoader handles random content without crashing."""
        for _ in range(20):
            content = FuzzGenerator.random_string(500)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                f.flush()

                loader = GuideLoader(f.name)
                try:
                    steps = loader.load()
                    # May or may not find valid steps
                except ValueError:
                    # Expected when no valid steps found
                    pass

            os.unlink(f.name)

    def test_unicode_fuzz_no_crash(self):
        """GuideLoader handles unicode fuzz without crashing."""
        for _ in range(20):
            content = f"Step 1: {FuzzGenerator.random_unicode(100)}\n"
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                                   delete=False, encoding='utf-8') as f:
                    f.write(content)
                    f.flush()

                    loader = GuideLoader(f.name)
                    try:
                        steps = loader.load()
                        self.assertEqual(len(steps), 1)
                    except ValueError:
                        pass

                os.unlink(f.name)
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

    def test_mutated_step_format(self):
        """GuideLoader handles mutated step formats."""
        base_formats = [
            "Step 1: Action",
            "Step 1 Action",
            "Step1: Action",
            "step 1: Action",
            "STEP 1: Action",
        ]

        for base in base_formats:
            for _ in range(5):
                mutated = FuzzGenerator.mutation_fuzz(base, mutations=3)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(f"{mutated}\n")
                    f.flush()

                    loader = GuideLoader(f.name)
                    try:
                        loader.load()
                    except ValueError:
                        pass

                os.unlink(f.name)

    def test_very_long_step_numbers(self):
        """GuideLoader handles very long step numbers."""
        large_numbers = [999999, 2**31, 2**63]

        for num in large_numbers:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f"Step {num}: Action\n")
                f.flush()

                loader = GuideLoader(f.name)
                try:
                    steps = loader.load()
                    self.assertEqual(len(steps), 1)
                except (ValueError, OverflowError):
                    pass

            os.unlink(f.name)


class TestConfigFuzzing(unittest.TestCase):
    """Fuzz testing for Config."""

    def test_random_json_values(self):
        """Config handles random JSON values."""
        for _ in range(20):
            data = {
                "model_a": FuzzGenerator.random_string(50),
                "temp_creative": random.random() * 2,  # 0-2
                "max_tokens": random.randint(-1000, 100000),
            }

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(data, f)
                f.flush()

                config = Config.from_json(f.name)
                self.assertIsInstance(config, Config)

            os.unlink(f.name)

    def test_deeply_nested_json(self):
        """Config handles deeply nested JSON structures."""
        depths = [10, 50, 100]

        for depth in depths:
            nested = {"value": "test"}
            for _ in range(depth):
                nested = {"nested": nested}

            data = {"model_a": "test", "extra": nested}

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(data, f)
                f.flush()

                try:
                    config = Config.from_json(f.name)
                    self.assertEqual(config.model_a, "test")
                except RecursionError:
                    pass  # Very deep nesting may cause this

            os.unlink(f.name)

    def test_special_json_values(self):
        """Config handles special JSON values."""
        special_values = [
            {"model_a": None},
            {"model_a": True},
            {"model_a": False},
            {"model_a": []},
            {"model_a": {}},
            {"model_a": [1, 2, 3]},
            {"model_a": {"nested": "value"}},
            {"temp_creative": float('inf')},  # May be serialized as null
            {"max_tokens": -99999999},
        ]

        for data in special_values:
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(data, f)
                    f.flush()

                    config = Config.from_json(f.name)
                    self.assertIsInstance(config, Config)

                os.unlink(f.name)
            except (ValueError, OverflowError, TypeError):
                pass


class TestCheckpointFuzzing(unittest.TestCase):
    """Fuzz testing for Checkpoint."""

    def test_random_checkpoint_data(self):
        """Checkpoint handles random data."""
        for _ in range(20):
            checkpoint = Checkpoint(
                guide_file=FuzzGenerator.random_string(50),
                spec=FuzzGenerator.random_string(200),
                completed_steps=random.randint(-100, 10000),
                cumulative_output=FuzzGenerator.random_string(1000),
                step_outputs=[FuzzGenerator.random_string(100) for _ in range(10)],
                timestamp=datetime.now().isoformat()
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "checkpoint.json")
                checkpoint.save(path)
                loaded = Checkpoint.load(path)

                self.assertEqual(checkpoint.guide_file, loaded.guide_file)
                self.assertEqual(checkpoint.spec, loaded.spec)

    def test_unicode_checkpoint_data(self):
        """Checkpoint handles unicode data."""
        for _ in range(10):
            try:
                checkpoint = Checkpoint(
                    guide_file="test.txt",
                    spec=FuzzGenerator.random_unicode(100),
                    completed_steps=5,
                    cumulative_output=FuzzGenerator.random_unicode(500),
                    step_outputs=[FuzzGenerator.random_unicode(50) for _ in range(5)],
                    timestamp=datetime.now().isoformat()
                )

                with tempfile.TemporaryDirectory() as tmpdir:
                    path = os.path.join(tmpdir, "checkpoint.json")
                    checkpoint.save(path)
                    loaded = Checkpoint.load(path)

                    self.assertEqual(checkpoint.spec, loaded.spec)
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass


class TestStateManagerBehavior(unittest.TestCase):
    """Test StateManager runtime behavior."""

    def test_add_many_outputs(self):
        """StateManager handles many step outputs."""
        manager = StateManager()

        for i in range(1000):
            manager.add_step_output(f"Output for step {i}")

        self.assertEqual(manager.current_step_index, 1000)
        self.assertEqual(len(manager.step_outputs), 1000)

    def test_large_output_accumulation(self):
        """StateManager handles large cumulative output."""
        manager = StateManager()

        for i in range(100):
            large_output = "x" * 10000  # 10KB per step
            manager.add_step_output(large_output)

        # Should have ~1MB+ of cumulative output
        self.assertGreater(len(manager.cumulative_output), 1000000)

    def test_context_retrieval(self):
        """StateManager context retrieval works correctly."""
        manager = StateManager()

        manager.add_step_output("First output")
        manager.add_step_output("Second output")

        context = manager.get_context()

        self.assertIn("First output", context)
        self.assertIn("Second output", context)
        self.assertIn("Step 1", context)
        self.assertIn("Step 2", context)


class TestRuntimeStability(unittest.TestCase):
    """Test overall runtime stability."""

    def test_repeated_operations(self):
        """System handles repeated operations without degradation."""
        for _ in range(100):
            # Create and load config
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump({"model_a": "test"}, f)
                f.flush()
                Config.from_json(f.name)
            os.unlink(f.name)

            # Create and load guide
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Step 1: Test\n")
                f.flush()
                loader = GuideLoader(f.name)
                loader.load()
            os.unlink(f.name)

    def test_concurrent_file_operations(self):
        """System handles concurrent file operations."""
        import concurrent.futures

        def operation(i):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump({"model_a": f"model_{i}"}, f)
                config_file = f.name

            config = Config.from_json(config_file)
            os.unlink(config_file)
            return config.model_a

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(operation, i) for i in range(50)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 50)

    def test_rapid_state_transitions(self):
        """StateManager handles rapid state transitions."""
        manager = StateManager()

        for i in range(1000):
            manager.add_step_output(f"Quick output {i}")
            _ = manager.get_context()

        self.assertEqual(manager.current_step_index, 1000)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_guide_file(self):
        """GuideLoader handles empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")  # Empty file
            f.flush()

            loader = GuideLoader(f.name)
            with self.assertRaises(ValueError):
                loader.load()

        os.unlink(f.name)

    def test_whitespace_only_guide(self):
        """GuideLoader handles whitespace-only file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("   \n\t\n   ")
            f.flush()

            loader = GuideLoader(f.name)
            with self.assertRaises(ValueError):
                loader.load()

        os.unlink(f.name)

    def test_config_empty_json(self):
        """Config handles empty JSON object."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{}")
            f.flush()

            config = Config.from_json(f.name)
            # Should use defaults
            self.assertIsNotNone(config.model_a)

        os.unlink(f.name)

    def test_checkpoint_empty_outputs(self):
        """Checkpoint handles empty step outputs."""
        checkpoint = Checkpoint(
            guide_file="test.txt",
            spec="",
            completed_steps=0,
            cumulative_output="",
            step_outputs=[],
            timestamp=datetime.now().isoformat()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "checkpoint.json")
            checkpoint.save(path)
            loaded = Checkpoint.load(path)

            self.assertEqual(loaded.completed_steps, 0)
            self.assertEqual(loaded.step_outputs, [])


class TestResourceLeaks(unittest.TestCase):
    """Test for resource leaks."""

    def test_file_handles_closed(self):
        """File handles are properly closed after operations."""
        import gc

        files_before = self._count_open_files()

        for _ in range(100):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Step 1: Test\n")
                name = f.name

            loader = GuideLoader(name)
            loader.load()
            os.unlink(name)

        gc.collect()
        files_after = self._count_open_files()

        # Should not have leaked file handles
        self.assertLessEqual(files_after, files_before + 5)

    def _count_open_files(self) -> int:
        """Count open file descriptors (Linux only)."""
        try:
            return len(os.listdir('/proc/self/fd'))
        except FileNotFoundError:
            return 0  # Not on Linux


if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)
    unittest.main(verbosity=2)
