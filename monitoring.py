#!/usr/bin/env python3
"""
Monitoring module for Code Cobra.

Provides health checks, uptime monitoring, error tracking, and
performance monitoring capabilities.
"""

import json
import os
import signal
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Import telemetry if available
try:
    from telemetry import MetricsCollector, get_collector
except ImportError:
    MetricsCollector = None
    get_collector = lambda: None


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System-level metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_percent: float = 0.0
    open_files: int = 0
    thread_count: int = 0
    uptime_seconds: float = 0.0


class HealthChecker:
    """Manages health checks for the application."""

    def __init__(self):
        self.checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self._start_time = datetime.now()

    def register_check(self, name: str,
                       check_fn: Callable[[], HealthCheckResult]) -> None:
        """Register a health check function."""
        self.checks[name] = check_fn

    def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not found"
            )

        start = time.perf_counter()
        try:
            result = self.checks[name]()
            result.duration_ms = (time.perf_counter() - start) * 1000
            self.last_results[name] = result
            return result
        except Exception as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.perf_counter() - start) * 1000
            )
            self.last_results[name] = result
            return result

    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        for name in self.checks:
            results[name] = self.run_check(name)
        return results

    def get_overall_status(self) -> HealthStatus:
        """Get overall health status based on all checks."""
        if not self.last_results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in self.last_results.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    def get_uptime(self) -> timedelta:
        """Get application uptime."""
        return datetime.now() - self._start_time

    def to_dict(self) -> Dict[str, Any]:
        """Export health status as dictionary."""
        return {
            "status": self.get_overall_status().value,
            "uptime_seconds": self.get_uptime().total_seconds(),
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "duration_ms": result.duration_ms,
                    "timestamp": result.timestamp,
                    "details": result.details
                }
                for name, result in self.last_results.items()
            }
        }


class ErrorTracker:
    """Tracks and aggregates errors."""

    def __init__(self, max_errors: int = 1000):
        self.errors: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}
        self.max_errors = max_errors
        self._lock = threading.Lock()

    def record_error(self, error_type: str, message: str,
                     context: Optional[Dict[str, Any]] = None) -> None:
        """Record an error occurrence."""
        with self._lock:
            error_entry = {
                "type": error_type,
                "message": message,
                "context": context or {},
                "timestamp": datetime.now().isoformat()
            }

            self.errors.append(error_entry)
            if len(self.errors) > self.max_errors:
                self.errors.pop(0)

            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

            # Update telemetry if available
            collector = get_collector()
            if collector:
                collector.increment_counter(f"errors.{error_type}")

    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get most recent errors."""
        with self._lock:
            return self.errors[-count:]

    def get_error_summary(self) -> Dict[str, int]:
        """Get error count by type."""
        with self._lock:
            return dict(self.error_counts)

    def clear(self) -> None:
        """Clear all tracked errors."""
        with self._lock:
            self.errors.clear()
            self.error_counts.clear()


class PerformanceMonitor:
    """Monitors application performance."""

    def __init__(self, sample_interval: float = 60.0):
        self.sample_interval = sample_interval
        self.samples: List[SystemMetrics] = []
        self.max_samples = 1440  # 24 hours at 1-minute intervals
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time = datetime.now()

    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        metrics = SystemMetrics()

        try:
            # Get uptime
            metrics.uptime_seconds = (datetime.now() - self._start_time).total_seconds()

            # Thread count
            metrics.thread_count = threading.active_count()

            # Try to get process info (requires psutil, fallback gracefully)
            try:
                import psutil
                process = psutil.Process()

                metrics.cpu_percent = process.cpu_percent()
                mem_info = process.memory_info()
                metrics.memory_used_mb = mem_info.rss / (1024 * 1024)
                metrics.memory_percent = process.memory_percent()
                metrics.open_files = len(process.open_files())

                # Disk usage
                disk = psutil.disk_usage('/')
                metrics.disk_percent = disk.percent
            except ImportError:
                # psutil not available, use basic metrics
                pass
            except Exception:
                pass

        except Exception:
            pass

        return metrics

    def sample(self) -> SystemMetrics:
        """Take a performance sample."""
        metrics = self.get_system_metrics()
        self.samples.append(metrics)

        if len(self.samples) > self.max_samples:
            self.samples.pop(0)

        # Update telemetry
        collector = get_collector()
        if collector:
            collector.record_gauge("cpu_percent", metrics.cpu_percent)
            collector.record_gauge("memory_percent", metrics.memory_percent)
            collector.record_gauge("memory_used_mb", metrics.memory_used_mb)
            collector.record_gauge("thread_count", metrics.thread_count)

        return metrics

    def start_background_sampling(self) -> None:
        """Start background performance sampling."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop_background_sampling(self) -> None:
        """Stop background sampling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _sample_loop(self) -> None:
        """Background sampling loop."""
        while self._running:
            self.sample()
            time.sleep(self.sample_interval)

    def get_average_metrics(self, minutes: int = 5) -> SystemMetrics:
        """Get average metrics over the last N minutes."""
        samples_needed = int(minutes * 60 / self.sample_interval)
        recent = self.samples[-samples_needed:] if self.samples else []

        if not recent:
            return SystemMetrics()

        return SystemMetrics(
            cpu_percent=sum(s.cpu_percent for s in recent) / len(recent),
            memory_percent=sum(s.memory_percent for s in recent) / len(recent),
            memory_used_mb=sum(s.memory_used_mb for s in recent) / len(recent),
            disk_percent=sum(s.disk_percent for s in recent) / len(recent),
            open_files=int(sum(s.open_files for s in recent) / len(recent)),
            thread_count=int(sum(s.thread_count for s in recent) / len(recent)),
            uptime_seconds=recent[-1].uptime_seconds if recent else 0
        )


class MonitoringService:
    """Central monitoring service combining all monitors."""

    def __init__(self):
        self.health_checker = HealthChecker()
        self.error_tracker = ErrorTracker()
        self.performance_monitor = PerformanceMonitor()

        # Register default health checks
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default health checks."""

        # Application check
        def app_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="application",
                status=HealthStatus.HEALTHY,
                message="Application is running"
            )

        self.health_checker.register_check("application", app_check)

        # Memory check
        def memory_check() -> HealthCheckResult:
            metrics = self.performance_monitor.get_system_metrics()
            if metrics.memory_percent > 90:
                return HealthCheckResult(
                    name="memory",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Memory usage critical: {metrics.memory_percent:.1f}%",
                    details={"memory_percent": metrics.memory_percent}
                )
            elif metrics.memory_percent > 75:
                return HealthCheckResult(
                    name="memory",
                    status=HealthStatus.DEGRADED,
                    message=f"Memory usage high: {metrics.memory_percent:.1f}%",
                    details={"memory_percent": metrics.memory_percent}
                )
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.HEALTHY,
                message=f"Memory usage normal: {metrics.memory_percent:.1f}%",
                details={"memory_percent": metrics.memory_percent}
            )

        self.health_checker.register_check("memory", memory_check)

        # Config check
        def config_check() -> HealthCheckResult:
            try:
                # Check if config files exist
                config_files = ["config/dev.json", "config/prod.json"]
                missing = [f for f in config_files if not os.path.exists(f)]
                if missing:
                    return HealthCheckResult(
                        name="config",
                        status=HealthStatus.DEGRADED,
                        message=f"Missing config files: {missing}",
                        details={"missing": missing}
                    )
                return HealthCheckResult(
                    name="config",
                    status=HealthStatus.HEALTHY,
                    message="Configuration files present"
                )
            except Exception as e:
                return HealthCheckResult(
                    name="config",
                    status=HealthStatus.UNHEALTHY,
                    message=str(e)
                )

        self.health_checker.register_check("config", config_check)

    def start(self) -> None:
        """Start all monitoring services."""
        self.performance_monitor.start_background_sampling()

    def stop(self) -> None:
        """Stop all monitoring services."""
        self.performance_monitor.stop_background_sampling()

    def get_health(self) -> Dict[str, Any]:
        """Get current health status."""
        self.health_checker.run_all_checks()
        return self.health_checker.to_dict()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        current = self.performance_monitor.get_system_metrics()
        avg_5m = self.performance_monitor.get_average_metrics(5)
        avg_15m = self.performance_monitor.get_average_metrics(15)

        return {
            "current": asdict(current),
            "avg_5m": asdict(avg_5m),
            "avg_15m": asdict(avg_15m),
            "error_summary": self.error_tracker.get_error_summary(),
            "recent_errors": self.error_tracker.get_recent_errors(5)
        }

    def export_json(self) -> str:
        """Export full monitoring status as JSON."""
        return json.dumps({
            "health": self.get_health(),
            "metrics": self.get_metrics(),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


# Global monitoring service
_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get or create the global monitoring service."""
    global _service
    if _service is None:
        _service = MonitoringService()
    return _service


def record_error(error_type: str, message: str,
                 context: Optional[Dict[str, Any]] = None) -> None:
    """Record an error via the global monitoring service."""
    get_monitoring_service().error_tracker.record_error(error_type, message, context)


def health_check() -> Dict[str, Any]:
    """Run health checks and return status."""
    return get_monitoring_service().get_health()


# Example usage
if __name__ == "__main__":
    # Create and start monitoring
    service = get_monitoring_service()
    service.start()

    print("=== Health Check ===")
    print(json.dumps(service.get_health(), indent=2))

    # Simulate some errors
    record_error("connection_error", "Failed to connect to Ollama")
    record_error("timeout_error", "Request timed out")
    record_error("connection_error", "Failed to connect to Ollama")

    print("\n=== Metrics ===")
    print(json.dumps(service.get_metrics(), indent=2))

    print("\n=== Full Export ===")
    print(service.export_json())

    service.stop()
