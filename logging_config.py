#!/usr/bin/env python3
"""
Structured logging configuration for Autonomous Coding Ensemble System.

Provides JSON-formatted logs suitable for ELK stack, CloudWatch, or similar.
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON for structured logging.

    Compatible with ELK stack, CloudWatch, Datadog, and other log aggregators.
    """

    def __init__(self, include_timestamp: bool = True, include_level: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "message": record.getMessage(),
            "logger": record.name,
        }

        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        if self.include_level:
            log_data["level"] = record.levelname
            log_data["level_num"] = record.levelno

        # Add source location
        log_data["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "asctime"
            ):
                log_data[key] = value

        return json.dumps(log_data, default=str)


class CodeCobraLogger:
    """
    Structured logger for Code Cobra application.

    Provides methods for logging workflow events, errors, and metrics.
    """

    def __init__(
        self,
        name: str = "code_cobra",
        level: int = logging.INFO,
        json_format: bool = True,
        log_file: Optional[str] = None
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Remove existing handlers
        self.logger.handlers = []

        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        if json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                )
            )
        self.logger.addHandler(console_handler)

        # File handler (optional)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)

    def workflow_start(self, spec: str, guide_file: str, total_steps: int) -> None:
        """Log workflow start event."""
        self.logger.info(
            "Workflow started",
            extra={
                "event": "workflow_start",
                "spec_preview": spec[:100] if len(spec) > 100 else spec,
                "guide_file": guide_file,
                "total_steps": total_steps,
            }
        )

    def workflow_complete(self, output_file: str, total_steps: int) -> None:
        """Log workflow completion event."""
        self.logger.info(
            "Workflow completed",
            extra={
                "event": "workflow_complete",
                "output_file": output_file,
                "total_steps": total_steps,
            }
        )

    def step_start(self, step_number: int, total_steps: int, description: str) -> None:
        """Log step start event."""
        self.logger.info(
            f"Step {step_number}/{total_steps} started",
            extra={
                "event": "step_start",
                "step_number": step_number,
                "total_steps": total_steps,
                "description": description[:50],
            }
        )

    def step_complete(self, step_number: int, total_steps: int) -> None:
        """Log step completion event."""
        self.logger.info(
            f"Step {step_number}/{total_steps} completed",
            extra={
                "event": "step_complete",
                "step_number": step_number,
                "total_steps": total_steps,
            }
        )

    def model_query(
        self,
        model: str,
        stage: str,
        iteration: Optional[int] = None
    ) -> None:
        """Log model query event."""
        self.logger.debug(
            f"Querying model: {model}",
            extra={
                "event": "model_query",
                "model": model,
                "stage": stage,
                "iteration": iteration,
            }
        )

    def model_response(
        self,
        model: str,
        stage: str,
        response_length: int,
        iteration: Optional[int] = None
    ) -> None:
        """Log model response event."""
        self.logger.debug(
            f"Model response received: {response_length} chars",
            extra={
                "event": "model_response",
                "model": model,
                "stage": stage,
                "response_length": response_length,
                "iteration": iteration,
            }
        )

    def convergence_detected(self, stage: str, iteration: int) -> None:
        """Log convergence detection event."""
        self.logger.info(
            f"Convergence detected at iteration {iteration}",
            extra={
                "event": "convergence",
                "stage": stage,
                "iteration": iteration,
            }
        )

    def checkpoint_saved(self, checkpoint_file: str, completed_steps: int) -> None:
        """Log checkpoint save event."""
        self.logger.info(
            f"Checkpoint saved: {checkpoint_file}",
            extra={
                "event": "checkpoint_saved",
                "checkpoint_file": checkpoint_file,
                "completed_steps": completed_steps,
            }
        )

    def checkpoint_loaded(self, checkpoint_file: str, completed_steps: int) -> None:
        """Log checkpoint load event."""
        self.logger.info(
            f"Checkpoint loaded: {checkpoint_file}",
            extra={
                "event": "checkpoint_loaded",
                "checkpoint_file": checkpoint_file,
                "completed_steps": completed_steps,
            }
        )

    def error(
        self,
        message: str,
        error_type: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log error event."""
        self.logger.error(
            message,
            extra={
                "event": "error",
                "error_type": error_type,
                **kwargs,
            }
        )

    def warning(self, message: str, **kwargs) -> None:
        """Log warning event."""
        self.logger.warning(
            message,
            extra={
                "event": "warning",
                **kwargs,
            }
        )

    def api_error(
        self,
        endpoint: str,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> None:
        """Log API error event."""
        self.logger.error(
            f"API error: {endpoint}",
            extra={
                "event": "api_error",
                "endpoint": endpoint,
                "status_code": status_code,
                "error_message": error_message,
                "retry_count": retry_count,
            }
        )

    def api_retry(self, endpoint: str, attempt: int, max_attempts: int) -> None:
        """Log API retry event."""
        self.logger.warning(
            f"Retrying API call: attempt {attempt}/{max_attempts}",
            extra={
                "event": "api_retry",
                "endpoint": endpoint,
                "attempt": attempt,
                "max_attempts": max_attempts,
            }
        )


# Global logger instance
logger = CodeCobraLogger(json_format=False)


def configure_logging(
    level: int = logging.INFO,
    json_format: bool = False,
    log_file: Optional[str] = None
) -> CodeCobraLogger:
    """
    Configure and return the global logger.

    Args:
        level: Logging level (default: INFO)
        json_format: Use JSON formatting (default: False for console)
        log_file: Optional log file path

    Returns:
        Configured CodeCobraLogger instance
    """
    global logger
    logger = CodeCobraLogger(
        level=level,
        json_format=json_format,
        log_file=log_file
    )
    return logger
