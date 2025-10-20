"""
Performance monitoring and metrics tracking.
Provides lightweight monitoring without external dependencies.
"""
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from functools import wraps
from app.logger import get_logger

logger = get_logger("core.monitoring")


class PerformanceMonitor:
    """Track performance metrics for the application."""

    def __init__(self):
        """Initialize the performance monitor."""
        self.start_time = datetime.utcnow()
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "total_response_time": 0.0,
            "llm_call_count": 0,
            "cache_hit_count": 0,
            "cache_miss_count": 0,
        }
        self.operation_times = {}

    def track_request(self, duration: float, success: bool = True):
        """
        Track a request completion.

        Args:
            duration: Request duration in seconds
            success: Whether request succeeded
        """
        self.metrics["request_count"] += 1
        self.metrics["total_response_time"] += duration
        if not success:
            self.metrics["error_count"] += 1

    def track_llm_call(self):
        """Track an LLM API call."""
        self.metrics["llm_call_count"] += 1

    def track_cache_hit(self):
        """Track a cache hit."""
        self.metrics["cache_hit_count"] += 1

    def track_cache_miss(self):
        """Track a cache miss."""
        self.metrics["cache_miss_count"] += 1

    def track_operation(self, operation: str, duration: float):
        """
        Track timing for a specific operation.

        Args:
            operation: Name of the operation
            duration: Duration in seconds
        """
        if operation not in self.operation_times:
            self.operation_times[operation] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0
            }

        stats = self.operation_times[operation]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot.

        Returns:
            Dictionary of metrics
        """
        request_count = self.metrics["request_count"]
        avg_response_time = (
            self.metrics["total_response_time"] / request_count
            if request_count > 0
            else 0.0
        )

        total_cache_ops = (
            self.metrics["cache_hit_count"] + self.metrics["cache_miss_count"]
        )
        cache_hit_rate = (
            self.metrics["cache_hit_count"] / total_cache_ops
            if total_cache_ops > 0
            else 0.0
        )

        error_rate = (
            self.metrics["error_count"] / request_count
            if request_count > 0
            else 0.0
        )

        # Calculate operation averages
        operations = {}
        for op_name, stats in self.operation_times.items():
            operations[op_name] = {
                "count": stats["count"],
                "avg_time": stats["total_time"] / stats["count"] if stats["count"] > 0 else 0.0,
                "min_time": stats["min_time"] if stats["min_time"] != float('inf') else 0.0,
                "max_time": stats["max_time"]
            }

        return {
            "requests": {
                "total": request_count,
                "errors": self.metrics["error_count"],
                "error_rate": error_rate,
                "avg_response_time": avg_response_time
            },
            "llm": {
                "total_calls": self.metrics["llm_call_count"]
            },
            "cache": {
                "hits": self.metrics["cache_hit_count"],
                "misses": self.metrics["cache_miss_count"],
                "hit_rate": cache_hit_rate
            },
            "operations": operations,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
        }

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "total_response_time": 0.0,
            "llm_call_count": 0,
            "cache_hit_count": 0,
            "cache_miss_count": 0,
        }
        self.operation_times = {}


# Global monitor instance
_monitor = PerformanceMonitor()


def get_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _monitor


def track_time(operation: str):
    """
    Decorator to track operation timing.

    Args:
        operation: Name of the operation to track

    Example:
        @track_time("document_generation")
        async def generate_document(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                _monitor.track_operation(operation, duration)
                return result
            except Exception as e:
                duration = time.time() - start
                _monitor.track_operation(operation, duration)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                _monitor.track_operation(operation, duration)
                return result
            except Exception as e:
                duration = time.time() - start
                _monitor.track_operation(operation, duration)
                raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_system_metrics() -> Dict[str, Any]:
    """
    Get system-level metrics.

    Returns:
        Dictionary of system metrics
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024 * 1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_available_mb": 0,
            "disk_percent": 0,
            "disk_free_gb": 0,
            "error": str(e)
        }
