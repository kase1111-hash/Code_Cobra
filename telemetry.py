#!/usr/bin/env python3
"""
Telemetry and metrics collection for Code Cobra.

Provides lightweight metrics collection for monitoring system performance,
usage patterns, and error tracking.
"""

import json
import os
import threading
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional


@dataclass
class MetricPoint:
    """A single metric measurement."""
    name: str
    value: float
    timestamp: str
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram


@dataclass
class WorkflowMetrics:
    """Metrics for a workflow execution."""
    workflow_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    model_a_calls: int = 0
    model_b_calls: int = 0
    model_c_calls: int = 0
    total_tokens: int = 0
    errors: List[str] = field(default_factory=list)
    status: str = "running"


class MetricsCollector:
    """Collects and aggregates metrics."""

    def __init__(self, app_name: str = "code_cobra"):
        self.app_name = app_name
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.workflows: Dict[str, WorkflowMetrics] = {}
        self._lock = threading.Lock()
        self._start_time = datetime.now()

    def record_gauge(self, name: str, value: float,
                     labels: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric (current value)."""
        with self._lock:
            self.gauges[name] = value
            self.metrics[name].append(MetricPoint(
                name=name,
                value=value,
                timestamp=datetime.now().isoformat(),
                labels=labels or {},
                metric_type="gauge"
            ))

    def increment_counter(self, name: str, value: float = 1.0,
                          labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            self.counters[name] += value
            self.metrics[name].append(MetricPoint(
                name=name,
                value=self.counters[name],
                timestamp=datetime.now().isoformat(),
                labels=labels or {},
                metric_type="counter"
            ))

    def record_histogram(self, name: str, value: float,
                         labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value (for distribution analysis)."""
        with self._lock:
            self.histograms[name].append(value)
            self.metrics[name].append(MetricPoint(
                name=name,
                value=value,
                timestamp=datetime.now().isoformat(),
                labels=labels or {},
                metric_type="histogram"
            ))

    def start_workflow(self, workflow_id: str, total_steps: int) -> None:
        """Start tracking a workflow."""
        with self._lock:
            self.workflows[workflow_id] = WorkflowMetrics(
                workflow_id=workflow_id,
                start_time=datetime.now().isoformat(),
                total_steps=total_steps
            )
            self.increment_counter("workflows_started")

    def complete_step(self, workflow_id: str, model_used: str,
                      tokens: int = 0) -> None:
        """Record step completion."""
        with self._lock:
            if workflow_id in self.workflows:
                wf = self.workflows[workflow_id]
                wf.completed_steps += 1
                wf.total_tokens += tokens

                if model_used == "model_a":
                    wf.model_a_calls += 1
                elif model_used == "model_b":
                    wf.model_b_calls += 1
                elif model_used == "model_c":
                    wf.model_c_calls += 1

                self.increment_counter("steps_completed")
                self.record_histogram("tokens_per_step", tokens)

    def fail_step(self, workflow_id: str, error: str) -> None:
        """Record step failure."""
        with self._lock:
            if workflow_id in self.workflows:
                wf = self.workflows[workflow_id]
                wf.failed_steps += 1
                wf.errors.append(error)

                self.increment_counter("steps_failed")
                self.increment_counter(f"errors.{error[:50]}")

    def end_workflow(self, workflow_id: str, status: str = "completed") -> None:
        """End workflow tracking."""
        with self._lock:
            if workflow_id in self.workflows:
                wf = self.workflows[workflow_id]
                wf.end_time = datetime.now().isoformat()
                wf.status = status

                start = datetime.fromisoformat(wf.start_time)
                end = datetime.fromisoformat(wf.end_time)
                wf.duration_seconds = (end - start).total_seconds()

                self.increment_counter(f"workflows_{status}")
                self.record_histogram("workflow_duration", wf.duration_seconds)

    def get_workflow_metrics(self, workflow_id: str) -> Optional[WorkflowMetrics]:
        """Get metrics for a specific workflow."""
        return self.workflows.get(workflow_id)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        with self._lock:
            uptime = (datetime.now() - self._start_time).total_seconds()

            histogram_stats = {}
            for name, values in self.histograms.items():
                if values:
                    sorted_vals = sorted(values)
                    histogram_stats[name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": sum(values) / len(values),
                        "p50": sorted_vals[len(values) // 2],
                        "p95": sorted_vals[int(len(values) * 0.95)] if len(values) > 1 else sorted_vals[0],
                        "p99": sorted_vals[int(len(values) * 0.99)] if len(values) > 1 else sorted_vals[0],
                    }

            active_workflows = sum(
                1 for wf in self.workflows.values()
                if wf.status == "running"
            )

            return {
                "app_name": self.app_name,
                "uptime_seconds": uptime,
                "timestamp": datetime.now().isoformat(),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": histogram_stats,
                "active_workflows": active_workflows,
                "total_workflows": len(self.workflows),
            }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        prefix = self.app_name

        # Counters
        for name, value in self.counters.items():
            safe_name = name.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE {prefix}_{safe_name} counter")
            lines.append(f"{prefix}_{safe_name} {value}")

        # Gauges
        for name, value in self.gauges.items():
            safe_name = name.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE {prefix}_{safe_name} gauge")
            lines.append(f"{prefix}_{safe_name} {value}")

        # Histogram summaries
        for name, values in self.histograms.items():
            if values:
                safe_name = name.replace(".", "_").replace("-", "_")
                sorted_vals = sorted(values)
                count = len(values)
                total = sum(values)

                lines.append(f"# TYPE {prefix}_{safe_name} histogram")
                lines.append(f'{prefix}_{safe_name}_count {count}')
                lines.append(f'{prefix}_{safe_name}_sum {total}')

                # Quantiles
                for q in [0.5, 0.9, 0.95, 0.99]:
                    idx = int(count * q)
                    lines.append(f'{prefix}_{safe_name}{{quantile="{q}"}} {sorted_vals[min(idx, count-1)]}')

        return "\n".join(lines)

    def export_json(self) -> str:
        """Export metrics as JSON."""
        return json.dumps(self.get_summary(), indent=2)


class Timer:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, metric_name: str,
                 labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        duration = time.perf_counter() - self.start_time
        self.collector.record_histogram(self.metric_name, duration, self.labels)

        if exc_type is not None:
            self.collector.increment_counter(
                f"{self.metric_name}_errors",
                labels=self.labels
            )


def timed(collector: MetricsCollector, metric_name: str):
    """Decorator for timing function execution."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with Timer(collector, metric_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Global metrics collector instance
_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def configure_collector(app_name: str = "code_cobra") -> MetricsCollector:
    """Configure the global metrics collector."""
    global _collector
    _collector = MetricsCollector(app_name)
    return _collector


# Convenience functions
def record_gauge(name: str, value: float,
                 labels: Optional[Dict[str, str]] = None) -> None:
    """Record a gauge metric."""
    get_collector().record_gauge(name, value, labels)


def increment_counter(name: str, value: float = 1.0,
                      labels: Optional[Dict[str, str]] = None) -> None:
    """Increment a counter."""
    get_collector().increment_counter(name, value, labels)


def record_histogram(name: str, value: float,
                     labels: Optional[Dict[str, str]] = None) -> None:
    """Record a histogram value."""
    get_collector().record_histogram(name, value, labels)


def time_operation(metric_name: str,
                   labels: Optional[Dict[str, str]] = None) -> Timer:
    """Create a timer context manager."""
    return Timer(get_collector(), metric_name, labels)


# Example usage
if __name__ == "__main__":
    # Configure collector
    collector = configure_collector("code_cobra")

    # Simulate workflow
    workflow_id = "wf-001"
    collector.start_workflow(workflow_id, total_steps=5)

    # Simulate steps
    for i in range(5):
        with time_operation("step_duration"):
            time.sleep(0.1)  # Simulate work
            collector.complete_step(workflow_id, "model_a", tokens=100)

    collector.end_workflow(workflow_id)

    # Print summary
    print("=== Metrics Summary ===")
    print(collector.export_json())

    print("\n=== Prometheus Format ===")
    print(collector.export_prometheus())
