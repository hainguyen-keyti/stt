"""
Performance Timing Utilities

Provides decorators and context managers for measuring and logging
execution time of tasks for benchmarking purposes.
"""

import time
import logging
import functools
from typing import Optional, Callable, Any
from contextlib import contextmanager
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TaskMetrics:
    """Metrics for a single task execution."""
    task_name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark the task as complete and calculate duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error


class PerformanceLogger:
    """
    Logger for tracking and reporting task performance.

    Usage:
        perf = PerformanceLogger("STT")
        with perf.measure("transcribe", audio_duration=60.5):
            # do work
            pass
    """

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.logger = logging.getLogger(f"perf.{module_name}")

    @contextmanager
    def measure(self, task_name: str, **metadata):
        """
        Context manager to measure task execution time.

        Args:
            task_name: Name of the task being measured
            **metadata: Additional metadata to log (e.g., file_size, model_name)

        Yields:
            TaskMetrics object that will be populated with timing info
        """
        metrics = TaskMetrics(
            task_name=task_name,
            start_time=time.time(),
            metadata=metadata,
        )

        # Log start
        meta_str = ", ".join(f"{k}={v}" for k, v in metadata.items()) if metadata else ""
        self.logger.info(f"[{self.module_name}] START: {task_name}" + (f" ({meta_str})" if meta_str else ""))

        try:
            yield metrics
            metrics.complete(success=True)
        except Exception as e:
            metrics.complete(success=False, error=str(e))
            raise
        finally:
            # Log completion
            status = "OK" if metrics.success else f"FAILED: {metrics.error}"
            self.logger.info(
                f"[{self.module_name}] END: {task_name} - {metrics.duration_ms:.2f}ms [{status}]"
            )

    def log_step(self, step_name: str, duration_ms: float, **metadata):
        """Log a single step with timing."""
        meta_str = ", ".join(f"{k}={v}" for k, v in metadata.items()) if metadata else ""
        self.logger.info(
            f"[{self.module_name}] STEP: {step_name} - {duration_ms:.2f}ms" + (f" ({meta_str})" if meta_str else "")
        )

    def log_summary(self, task_name: str, total_ms: float, steps: dict, **metadata):
        """
        Log a summary of task execution with breakdown.

        Args:
            task_name: Name of the overall task
            total_ms: Total execution time in milliseconds
            steps: Dict of step_name -> duration_ms
            **metadata: Additional metadata
        """
        self.logger.info(f"[{self.module_name}] SUMMARY: {task_name}")
        self.logger.info(f"  Total: {total_ms:.2f}ms")

        for step_name, duration in steps.items():
            pct = (duration / total_ms * 100) if total_ms > 0 else 0
            self.logger.info(f"  - {step_name}: {duration:.2f}ms ({pct:.1f}%)")

        if metadata:
            for key, value in metadata.items():
                self.logger.info(f"  {key}: {value}")


def timed(task_name: Optional[str] = None, module: str = "default"):
    """
    Decorator to measure and log function execution time.

    Args:
        task_name: Name for the task (defaults to function name)
        module: Module name for logging

    Usage:
        @timed("process_audio", module="STT")
        def process_audio(file_path):
            # do work
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            name = task_name or func.__name__
            perf = PerformanceLogger(module)

            with perf.measure(name):
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            name = task_name or func.__name__
            perf = PerformanceLogger(module)

            with perf.measure(name):
                return await func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


class TaskTimer:
    """
    Simple timer for measuring task duration with step tracking.

    Usage:
        timer = TaskTimer("transcription")
        timer.start()
        # load model
        timer.mark("model_load")
        # transcribe
        timer.mark("inference")
        # format output
        timer.mark("formatting")
        timer.stop()
        timer.log_summary()
    """

    def __init__(self, task_name: str, module: str = "default"):
        self.task_name = task_name
        self.module = module
        self.logger = logging.getLogger(f"perf.{module}")

        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._last_mark: Optional[float] = None
        self._steps: dict = {}
        self._metadata: dict = {}

    def start(self) -> "TaskTimer":
        """Start the timer."""
        self._start_time = time.time()
        self._last_mark = self._start_time
        self.logger.info(f"[{self.module}] START: {self.task_name}")
        return self

    def mark(self, step_name: str, **metadata) -> float:
        """
        Mark a step completion and record its duration.

        Args:
            step_name: Name of the completed step
            **metadata: Additional metadata for this step

        Returns:
            Duration of this step in milliseconds
        """
        now = time.time()
        if self._last_mark is None:
            self._last_mark = now

        duration_ms = (now - self._last_mark) * 1000
        self._steps[step_name] = duration_ms
        self._last_mark = now

        meta_str = ", ".join(f"{k}={v}" for k, v in metadata.items()) if metadata else ""
        self.logger.info(
            f"[{self.module}] STEP: {step_name} - {duration_ms:.2f}ms" + (f" ({meta_str})" if meta_str else "")
        )

        return duration_ms

    def stop(self) -> float:
        """
        Stop the timer.

        Returns:
            Total duration in milliseconds
        """
        self._end_time = time.time()
        return self.total_ms

    @property
    def total_ms(self) -> float:
        """Get total elapsed time in milliseconds."""
        if self._start_time is None:
            return 0.0
        end = self._end_time or time.time()
        return (end - self._start_time) * 1000

    def add_metadata(self, **kwargs):
        """Add metadata to the timer."""
        self._metadata.update(kwargs)

    def log_summary(self, **extra_metadata):
        """Log a summary of all steps."""
        self._metadata.update(extra_metadata)
        total = self.total_ms

        self.logger.info(f"[{self.module}] SUMMARY: {self.task_name}")
        self.logger.info(f"  Total: {total:.2f}ms ({total/1000:.2f}s)")

        # Log steps with percentages
        for step_name, duration in self._steps.items():
            pct = (duration / total * 100) if total > 0 else 0
            self.logger.info(f"  - {step_name}: {duration:.2f}ms ({pct:.1f}%)")

        # Log metadata
        for key, value in self._metadata.items():
            if isinstance(value, float):
                self.logger.info(f"  {key}: {value:.2f}")
            else:
                self.logger.info(f"  {key}: {value}")

    def get_metrics(self) -> dict:
        """Get all metrics as a dictionary."""
        return {
            "task_name": self.task_name,
            "total_ms": self.total_ms,
            "steps": self._steps.copy(),
            "metadata": self._metadata.copy(),
        }


def format_duration(ms: float) -> str:
    """Format duration in human-readable format."""
    if ms < 1000:
        return f"{ms:.2f}ms"
    elif ms < 60000:
        return f"{ms/1000:.2f}s"
    else:
        minutes = int(ms // 60000)
        seconds = (ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"


def calculate_rtf(audio_duration_s: float, processing_time_ms: float) -> float:
    """
    Calculate Real-Time Factor (RTF).

    RTF < 1 means faster than real-time.
    RTF = 1 means real-time.
    RTF > 1 means slower than real-time.

    Args:
        audio_duration_s: Duration of audio in seconds
        processing_time_ms: Processing time in milliseconds

    Returns:
        Real-Time Factor
    """
    if audio_duration_s <= 0:
        return 0.0
    processing_time_s = processing_time_ms / 1000
    return processing_time_s / audio_duration_s
