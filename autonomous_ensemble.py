#!/usr/bin/env python3
"""
Autonomous Coding Ensemble System
A multi-agent AI coding system for autonomous code generation and security hardening.

This local LLM ensemble leverages natural language programming principles to transform
prose-first specifications into production-ready code through AI-powered code review
and automated vulnerability scanning.
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

import requests


# =============================================================================
# Section 4.1: Configuration Object
# =============================================================================

@dataclass
class Config:
    """Configuration for the autonomous ensemble system."""
    ollama_api: str = "http://localhost:11434/api/generate"
    model_a: str = "qwen2.5-coder:7b"      # Creative model
    model_b: str = "deepseek-coder-v2:16b"  # Analytical model
    model_c: str = "codestral:22b"          # Adversarial model
    temp_creative: float = 0.8
    temp_analytical: float = 0.3
    temp_adversarial: float = 0.7
    max_tokens: int = 2000
    max_iterations: int = 3
    output_file: str = "final_output.txt"
    verbose: bool = False

    @classmethod
    def from_json(cls, path: str) -> "Config":
        """Load configuration from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.

        Supports loading from .env file if python-dotenv is available.
        Environment variables override defaults.
        """
        # Try to load .env file if dotenv is available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv not installed, use existing env vars

        def get_env(key: str, default: str) -> str:
            return os.environ.get(key, default)

        def get_env_float(key: str, default: float) -> float:
            val = os.environ.get(key)
            return float(val) if val is not None else default

        def get_env_int(key: str, default: int) -> int:
            val = os.environ.get(key)
            return int(val) if val is not None else default

        def get_env_bool(key: str, default: bool) -> bool:
            val = os.environ.get(key, "").lower()
            if val in ("true", "1", "yes"):
                return True
            elif val in ("false", "0", "no"):
                return False
            return default

        return cls(
            ollama_api=get_env("OLLAMA_API", cls.ollama_api),
            model_a=get_env("MODEL_A", cls.model_a),
            model_b=get_env("MODEL_B", cls.model_b),
            model_c=get_env("MODEL_C", cls.model_c),
            temp_creative=get_env_float("TEMP_CREATIVE", cls.temp_creative),
            temp_analytical=get_env_float("TEMP_ANALYTICAL", cls.temp_analytical),
            temp_adversarial=get_env_float("TEMP_ADVERSARIAL", cls.temp_adversarial),
            max_tokens=get_env_int("MAX_TOKENS", cls.max_tokens),
            max_iterations=get_env_int("MAX_ITERATIONS", cls.max_iterations),
            output_file=get_env("OUTPUT_FILE", cls.output_file),
            verbose=get_env_bool("VERBOSE", cls.verbose)
        )


# =============================================================================
# Section 4.2: Step Processing Context
# =============================================================================

@dataclass
class StepContext:
    """Context for processing a single step."""
    step_number: int
    step_description: str
    spec: str
    previous_output: str = ""
    draft: str = ""
    corrected: str = ""
    secured: str = ""


# =============================================================================
# Section 4.3: API Request Payload
# =============================================================================

@dataclass
class OllamaRequest:
    """Request payload for Ollama API."""
    model: str
    prompt: str
    temperature: float
    max_tokens: int = 2000
    stream: bool = False

    def to_dict(self) -> dict:
        """Convert to API request dictionary."""
        return {
            "model": self.model,
            "prompt": self.prompt,
            "options": {"temperature": self.temperature},
            "stream": self.stream,
            "max_tokens": self.max_tokens
        }


# =============================================================================
# Section 3.1: Guide Loader
# =============================================================================

class GuideLoader:
    """
    Loads and parses guide files containing step-by-step instructions.

    Guide File Format:
        Step 1: [Action description]
        Step 2: [Action description]
        ...
        Step N: [Action description]
    """

    STEP_PATTERN = re.compile(r"^Step\s+(\d+):\s*(.+)$", re.IGNORECASE)

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.steps: List[str] = []

    def load(self) -> List[str]:
        """
        Load and parse the guide file.

        Returns:
            Ordered list of step descriptions.

        Raises:
            FileNotFoundError: If guide file doesn't exist.
            ValueError: If no valid steps found in guide.
        """
        if not os.path.exists(self.file_path):
            available = self._list_available_guides()
            raise FileNotFoundError(
                f"Guide file not found: {self.file_path}\n"
                f"Available guides: {', '.join(available) if available else 'none'}"
            )

        steps_dict = {}
        with open(self.file_path, "r") as f:
            for line in f:
                line = line.strip()
                match = self.STEP_PATTERN.match(line)
                if match:
                    step_num = int(match.group(1))
                    step_desc = match.group(2).strip()
                    steps_dict[step_num] = step_desc

        if not steps_dict:
            raise ValueError(
                f"No valid steps found in {self.file_path}\n"
                "Expected format: 'Step N: [description]'"
            )

        # Return steps in order
        self.steps = [steps_dict[i] for i in sorted(steps_dict.keys())]
        return self.steps

    def _list_available_guides(self) -> List[str]:
        """List available guide files in the current directory."""
        directory = os.path.dirname(self.file_path) or "."
        if os.path.isdir(directory):
            return [f for f in os.listdir(directory) if f.endswith("_guide.txt")]
        return []


# =============================================================================
# Section 3.4: State Manager
# =============================================================================

@dataclass
class StateManager:
    """Manages workflow state across step processing."""
    cumulative_output: str = ""
    current_step_index: int = 0
    step_outputs: List[str] = field(default_factory=list)

    def add_step_output(self, output: str) -> None:
        """Add output from a completed step."""
        self.step_outputs.append(output)
        formatted = f"\n--- Step {self.current_step_index + 1} Output ---\n{output}\n"
        self.cumulative_output += formatted
        self.current_step_index += 1

    def get_context(self) -> str:
        """Get cumulative output as context for next step."""
        return self.cumulative_output


# =============================================================================
# Section 10.3: Checkpoint/Resume
# =============================================================================

@dataclass
class Checkpoint:
    """Checkpoint state for workflow resumption."""
    guide_file: str
    spec: str
    completed_steps: int
    cumulative_output: str
    step_outputs: List[str]
    timestamp: str

    def to_dict(self) -> dict:
        """Convert checkpoint to dictionary for JSON serialization."""
        return {
            "guide_file": self.guide_file,
            "spec": self.spec,
            "completed_steps": self.completed_steps,
            "cumulative_output": self.cumulative_output,
            "step_outputs": self.step_outputs,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """Create checkpoint from dictionary."""
        return cls(
            guide_file=data["guide_file"],
            spec=data["spec"],
            completed_steps=data["completed_steps"],
            cumulative_output=data["cumulative_output"],
            step_outputs=data["step_outputs"],
            timestamp=data["timestamp"]
        )

    def save(self, path: str) -> None:
        """Save checkpoint to file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Checkpoint":
        """Load checkpoint from file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


# =============================================================================
# Section 10.1: Custom Model Hooks
# =============================================================================

@dataclass
class PipelineHooks:
    """Optional hooks for custom processing between pipeline stages."""
    post_draft: Optional[Callable[[str], str]] = None
    post_correction: Optional[Callable[[str], str]] = None
    post_security: Optional[Callable[[str], str]] = None


# =============================================================================
# Ollama API Client
# =============================================================================

class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, config: Config):
        self.config = config
        self.retry_count = 3
        self.retry_delay = 1.0

    def query(self, request: OllamaRequest) -> str:
        """
        Send a query to the Ollama API.

        Args:
            request: The OllamaRequest to send.

        Returns:
            The model's response text.

        Raises:
            ConnectionError: If unable to connect after retries.
        """
        for attempt in range(self.retry_count):
            try:
                response = requests.post(
                    self.config.ollama_api,
                    json=request.to_dict(),
                    timeout=120
                )
                response.raise_for_status()
                return response.json().get("response", "")
            except requests.exceptions.ConnectionError as e:
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise ConnectionError(
                        f"Failed to connect to Ollama API at {self.config.ollama_api} "
                        f"after {self.retry_count} attempts: {e}"
                    )
            except requests.exceptions.Timeout:
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise TimeoutError(
                        f"Timeout waiting for model response after {self.retry_count} attempts"
                    )
        # All code paths either return or raise, this is unreachable
        raise RuntimeError("Unexpected state: retry loop completed without return or exception")


# =============================================================================
# Section 3.2 & 3.3: Model Pipeline & Iteration Controller
# =============================================================================

class ModelPipeline:
    """
    Three-stage model pipeline for code processing.

    Model A (Creative): Generate initial draft
    Model B (Analytical): Error correction with iteration
    Model C (Adversarial): Security hardening with iteration
    """

    def __init__(self, config: Config, client: OllamaClient, hooks: Optional[PipelineHooks] = None):
        self.config = config
        self.client = client
        self.hooks = hooks or PipelineHooks()

    def process(self, context: StepContext) -> str:
        """
        Process a step through all three pipeline stages.

        Args:
            context: The StepContext containing step information.

        Returns:
            The final secured output.
        """
        # Stage 1: Creative Draft (Model A)
        context.draft = self._creative_draft(context)
        if self.hooks.post_draft:
            context.draft = self.hooks.post_draft(context.draft)

        # Stage 2: Error Correction (Model B) - Iterative
        context.corrected = self._error_correction(context)
        if self.hooks.post_correction:
            context.corrected = self.hooks.post_correction(context.corrected)

        # Stage 3: Security Hardening (Model C) - Iterative
        context.secured = self._security_hardening(context)
        if self.hooks.post_security:
            context.secured = self.hooks.post_security(context.secured)

        return context.secured

    def _creative_draft(self, context: StepContext) -> str:
        """Generate creative draft using Model A."""
        prompt = self._build_creative_prompt(context)
        request = OllamaRequest(
            model=self.config.model_a,
            prompt=prompt,
            temperature=self.config.temp_creative,
            max_tokens=self.config.max_tokens
        )
        if self.config.verbose:
            print(f"  [Model A] Generating creative draft...")
        return self.client.query(request)

    def _error_correction(self, context: StepContext) -> str:
        """Iteratively correct errors using Model B."""
        current = context.draft
        for i in range(self.config.max_iterations):
            prompt = self._build_correction_prompt(context, current)
            request = OllamaRequest(
                model=self.config.model_b,
                prompt=prompt,
                temperature=self.config.temp_analytical,
                max_tokens=self.config.max_tokens
            )
            if self.config.verbose:
                print(f"  [Model B] Correction iteration {i + 1}...")
            new_output = self.client.query(request)

            # Convergence check
            if new_output == current:
                if self.config.verbose:
                    print(f"  [Model B] Converged at iteration {i + 1}")
                break
            current = new_output
        return current

    def _security_hardening(self, context: StepContext) -> str:
        """Iteratively harden security using Model C."""
        current = context.corrected
        for i in range(self.config.max_iterations):
            prompt = self._build_security_prompt(context, current)
            request = OllamaRequest(
                model=self.config.model_c,
                prompt=prompt,
                temperature=self.config.temp_adversarial,
                max_tokens=self.config.max_tokens
            )
            if self.config.verbose:
                print(f"  [Model C] Security iteration {i + 1}...")
            new_output = self.client.query(request)

            # Convergence check
            if new_output == current:
                if self.config.verbose:
                    print(f"  [Model C] Converged at iteration {i + 1}")
                break
            current = new_output
        return current

    def _build_creative_prompt(self, context: StepContext) -> str:
        """Build prompt for Model A (Creative Draft)."""
        return (
            f"{context.previous_output}\n"
            f"Apply this step to the spec '{context.spec}': {context.step_description}\n"
            f"Generate a creative draft of code or plan."
        )

    def _build_correction_prompt(self, context: StepContext, current_output: str) -> str:
        """Build prompt for Model B (Error Correction)."""
        return (
            f"{context.previous_output}\n"
            f"Strictly analyze this for errors, bugs, inefficiencies:\n"
            f"{current_output}\n"
            f"Correct without adding new features."
        )

    def _build_security_prompt(self, context: StepContext, current_output: str) -> str:
        """Build prompt for Model C (Security Scan)."""
        return (
            f"{context.previous_output}\n"
            f"Act as a hacker: Identify security flaws in the following and suggest fixes:\n"
            f"{current_output}\n"
            f"List vulnerabilities and provide corrected code."
        )


# =============================================================================
# Section 5: Processing Logic - Workflow Engine
# =============================================================================

class WorkflowEngine:
    """Main workflow engine coordinating the ensemble processing."""

    def __init__(self, config: Config, hooks: Optional[PipelineHooks] = None,
                 checkpoint_file: Optional[str] = None):
        self.config = config
        self.client = OllamaClient(config)
        self.pipeline = ModelPipeline(config, self.client, hooks)
        self.state = StateManager()
        self.checkpoint_file = checkpoint_file

    def run(self, spec: str, guide_file: str, resume_from: Optional[str] = None) -> str:
        """
        Run the complete workflow.

        Args:
            spec: Project specification (string or file path).
            guide_file: Path to the guide file.
            resume_from: Optional checkpoint file to resume from.

        Returns:
            The cumulative output from all steps.
        """
        # Load specification
        spec_content = spec
        if os.path.isfile(spec):
            with open(spec, "r") as f:
                spec_content = f.read()

        # Load guide
        loader = GuideLoader(guide_file)
        steps = loader.load()

        # Resume from checkpoint if provided
        start_step = 0
        if resume_from and os.path.exists(resume_from):
            checkpoint = Checkpoint.load(resume_from)
            print(f"Resuming from checkpoint: {resume_from}")
            print(f"  Previously completed: {checkpoint.completed_steps} steps")
            print(f"  Checkpoint timestamp: {checkpoint.timestamp}")

            # Restore state
            self.state.cumulative_output = checkpoint.cumulative_output
            self.state.step_outputs = checkpoint.step_outputs
            self.state.current_step_index = checkpoint.completed_steps
            start_step = checkpoint.completed_steps

        print(f"Loaded {len(steps)} steps from {guide_file}")
        print(f"Specification: {spec_content[:100]}..." if len(spec_content) > 100 else f"Specification: {spec_content}")
        if start_step > 0:
            print(f"Starting from step {start_step + 1}")
        print("-" * 60)

        # Process each step
        for i in range(start_step, len(steps)):
            step_desc = steps[i]
            print(f"\nProcessing Step {i + 1}/{len(steps)}: {step_desc[:50]}...")

            context = StepContext(
                step_number=i + 1,
                step_description=step_desc,
                spec=spec_content,
                previous_output=self.state.get_context()
            )

            step_output = self.pipeline.process(context)
            self.state.add_step_output(step_output)

            # Save checkpoint after each step
            if self.checkpoint_file:
                self._save_checkpoint(guide_file, spec_content)

            print(f"  Step {i + 1} complete.")

        # Write output
        with open(self.config.output_file, "w") as f:
            f.write(self.state.cumulative_output)

        print("-" * 60)
        print(f"Workflow complete. Output written to {self.config.output_file}")

        return self.state.cumulative_output

    def _save_checkpoint(self, guide_file: str, spec: str) -> None:
        """Save current state to checkpoint file."""
        checkpoint = Checkpoint(
            guide_file=guide_file,
            spec=spec,
            completed_steps=self.state.current_step_index,
            cumulative_output=self.state.cumulative_output,
            step_outputs=self.state.step_outputs,
            timestamp=datetime.now().isoformat()
        )
        checkpoint.save(self.checkpoint_file)
        if self.config.verbose:
            print(f"  Checkpoint saved: {self.checkpoint_file}")

    def dry_run(self, guide_file: str) -> None:
        """Parse and validate guide without running models."""
        loader = GuideLoader(guide_file)
        steps = loader.load()

        print(f"Dry run - Validated {len(steps)} steps:")
        for i, step in enumerate(steps, 1):
            print(f"  Step {i}: {step}")
        print("\nGuide validation successful.")


# =============================================================================
# Section 10.2: Guide Chaining
# =============================================================================

class GuideChain:
    """
    Execute multiple guides sequentially.

    Output of guide N becomes input context for guide N+1.
    """

    def __init__(self, config: Config, hooks: Optional[PipelineHooks] = None,
                 checkpoint_dir: Optional[str] = None):
        self.config = config
        self.hooks = hooks
        self.checkpoint_dir = checkpoint_dir
        self.chain_output: str = ""

    def run(self, spec: str, guide_files: List[str]) -> str:
        """
        Run multiple guides in sequence.

        Args:
            spec: Project specification (string or file path).
            guide_files: List of guide file paths to execute in order.

        Returns:
            The cumulative output from all guides.
        """
        print(f"Starting guide chain with {len(guide_files)} guides")
        print(f"Chain: {' -> '.join(guide_files)}")
        print("=" * 60)

        cumulative_context = ""

        for idx, guide_file in enumerate(guide_files):
            print(f"\n[Chain {idx + 1}/{len(guide_files)}] Processing: {guide_file}")
            print("=" * 60)

            # Set up checkpoint file for this guide
            checkpoint_file = None
            if self.checkpoint_dir:
                os.makedirs(self.checkpoint_dir, exist_ok=True)
                checkpoint_file = os.path.join(
                    self.checkpoint_dir,
                    f"checkpoint_{idx}_{os.path.basename(guide_file)}.json"
                )

            # Create engine with accumulated context
            engine_config = Config(
                ollama_api=self.config.ollama_api,
                model_a=self.config.model_a,
                model_b=self.config.model_b,
                model_c=self.config.model_c,
                temp_creative=self.config.temp_creative,
                temp_analytical=self.config.temp_analytical,
                temp_adversarial=self.config.temp_adversarial,
                max_tokens=self.config.max_tokens,
                max_iterations=self.config.max_iterations,
                output_file=f"output_{idx}_{os.path.basename(guide_file).replace('.txt', '')}.txt",
                verbose=self.config.verbose
            )

            engine = WorkflowEngine(engine_config, self.hooks, checkpoint_file)

            # Prepend accumulated context to spec
            enhanced_spec = spec
            if cumulative_context:
                enhanced_spec = f"Previous context:\n{cumulative_context}\n\nCurrent spec:\n{spec}"

            # Run this guide
            output = engine.run(enhanced_spec, guide_file)

            # Accumulate output for next guide
            cumulative_context += f"\n\n--- Output from {guide_file} ---\n{output}"

        # Write final combined output
        self.chain_output = cumulative_context
        final_output_file = self.config.output_file
        with open(final_output_file, "w") as f:
            f.write(cumulative_context)

        print("\n" + "=" * 60)
        print(f"Guide chain complete. Final output: {final_output_file}")

        return cumulative_context

    def dry_run(self, guide_files: List[str]) -> None:
        """Validate all guides in the chain without running models."""
        print(f"Dry run - Validating {len(guide_files)} guides in chain")
        print("-" * 60)

        total_steps = 0
        for idx, guide_file in enumerate(guide_files):
            loader = GuideLoader(guide_file)
            steps = loader.load()
            total_steps += len(steps)
            print(f"\n[{idx + 1}] {guide_file}: {len(steps)} steps")
            for i, step in enumerate(steps, 1):
                print(f"    Step {i}: {step[:60]}...")

        print("-" * 60)
        print(f"Chain validation successful. Total steps: {total_steps}")


# =============================================================================
# Section 9: CLI Interface
# =============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="autonomous_ensemble.py",
        description="Autonomous Coding Ensemble System - Multi-agent AI for code generation and security hardening"
    )

    parser.add_argument(
        "--spec",
        required=False,
        help="Project specification (string or file path)"
    )

    parser.add_argument(
        "--guide",
        default="coding_guide.txt",
        help="Path to guide file (default: coding_guide.txt)"
    )

    parser.add_argument(
        "--output",
        default="final_output.txt",
        help="Output file path (default: final_output.txt)"
    )

    parser.add_argument(
        "--config",
        help="Optional JSON config file for model overrides"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse guide and validate without running models"
    )

    # Checkpoint/Resume arguments
    parser.add_argument(
        "--checkpoint",
        help="Path to checkpoint file for saving progress after each step"
    )

    parser.add_argument(
        "--resume",
        help="Path to checkpoint file to resume from"
    )

    # Guide Chaining arguments
    parser.add_argument(
        "--chain",
        nargs="+",
        help="Chain multiple guides: --chain guide1.txt guide2.txt guide3.txt"
    )

    parser.add_argument(
        "--checkpoint-dir",
        help="Directory to store checkpoints when using guide chaining"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Load configuration
    if args.config:
        config = Config.from_json(args.config)
    else:
        config = Config()

    # Apply CLI overrides
    config.output_file = args.output
    config.verbose = args.verbose

    try:
        # Guide Chaining mode
        if args.chain:
            chain = GuideChain(config, checkpoint_dir=args.checkpoint_dir)

            if args.dry_run:
                chain.dry_run(args.chain)
            else:
                if not args.spec:
                    print("Error: --spec is required unless using --dry-run")
                    return 1
                chain.run(args.spec, args.chain)

        # Single guide mode
        else:
            engine = WorkflowEngine(config, checkpoint_file=args.checkpoint)

            if args.dry_run:
                engine.dry_run(args.guide)
            else:
                if not args.spec:
                    print("Error: --spec is required unless using --dry-run")
                    return 1
                engine.run(args.spec, args.guide, resume_from=args.resume)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except ConnectionError as e:
        print(f"Connection Error: {e}")
        return 1
    except TimeoutError as e:
        print(f"Timeout Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
