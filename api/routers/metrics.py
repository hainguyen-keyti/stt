"""
Metrics API Router

Provides performance metrics, request statistics, and resource utilization
for production monitoring and observability.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Dict
import threading

from fastapi import APIRouter
from api.models.responses import Metrics
from lib.utils.gpu import is_gpu_available, get_vram_info

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class MetricsCollector:
    """
    Collects and aggregates service metrics.

    Thread-safe metrics collection for request statistics, latency tracking,
    and resource utilization monitoring.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Request statistics
        self.requests_total = 0
        self.requests_successful = 0
        self.requests_failed = 0

        # Request timestamps (for rate calculation)
        self.request_times: deque = deque(maxlen=1000)  # Last 1000 requests

        # Inference time tracking
        self.inference_times: deque = deque(maxlen=1000)  # Last 1000 inference times

        # Model cache statistics
        self.cache_hits = 0
        self.cache_misses = 0

        # Per-endpoint statistics
        self.endpoint_stats: Dict[str, Dict] = defaultdict(
            lambda: {"count": 0, "errors": 0, "total_time_ms": 0.0}
        )

    def record_request(
        self,
        endpoint: str,
        inference_time_ms: float,
        success: bool = True,
        cache_hit: bool = False,
    ):
        """
        Record a completed request.

        Args:
            endpoint: API endpoint name
            inference_time_ms: Inference time in milliseconds
            success: Whether request succeeded
            cache_hit: Whether model was loaded from cache
        """
        with self._lock:
            # Update counters
            self.requests_total += 1
            if success:
                self.requests_successful += 1
            else:
                self.requests_failed += 1

            # Record timestamp
            self.request_times.append(time.time())

            # Record inference time
            self.inference_times.append(inference_time_ms)

            # Update cache statistics
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1

            # Update per-endpoint stats
            self.endpoint_stats[endpoint]["count"] += 1
            if not success:
                self.endpoint_stats[endpoint]["errors"] += 1
            self.endpoint_stats[endpoint]["total_time_ms"] += inference_time_ms

    def get_metrics(self) -> Dict:
        """
        Calculate and return current metrics.

        Returns:
            Dictionary of metric values
        """
        with self._lock:
            # Calculate request rate
            now = time.time()
            one_hour_ago = now - 3600
            one_minute_ago = now - 60

            # Count requests in last hour and minute
            requests_last_hour = sum(
                1 for t in self.request_times if t >= one_hour_ago
            )
            requests_last_minute = sum(
                1 for t in self.request_times if t >= one_minute_ago
            )
            requests_per_minute = requests_last_minute  # Already per minute

            # Calculate latency percentiles
            if self.inference_times:
                sorted_times = sorted(self.inference_times)
                count = len(sorted_times)

                avg_inference = sum(sorted_times) / count
                p50 = sorted_times[int(count * 0.50)]
                p95 = sorted_times[int(count * 0.95)]
                p99 = sorted_times[int(count * 0.99)]
            else:
                avg_inference = p50 = p95 = p99 = 0.0

            # Calculate cache hit rate
            total_cache_requests = self.cache_hits + self.cache_misses
            cache_hit_rate = (
                self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0
            )

            # Calculate error rate
            error_rate = (
                self.requests_failed / self.requests_total
                if self.requests_total > 0
                else 0.0
            )

            # Get GPU metrics if available
            gpu_utilization = None
            vram_usage_percent = None

            if is_gpu_available():
                try:
                    vram_info = get_vram_info()
                    vram_usage_percent = vram_info.get("usage_percent")
                    # Note: GPU utilization requires nvidia-ml-py3 or pynvml
                    # For now, we'll leave it as None
                except Exception as e:
                    logger.warning(f"Failed to get GPU metrics: {e}")

            return {
                "requests_total": self.requests_total,
                "requests_last_hour": requests_last_hour,
                "requests_per_minute": float(requests_per_minute),
                "avg_inference_time_ms": avg_inference,
                "p50_inference_time_ms": p50,
                "p95_inference_time_ms": p95,
                "p99_inference_time_ms": p99,
                "gpu_utilization_percent": gpu_utilization,
                "vram_usage_percent": vram_usage_percent,
                "cache_hit_rate": cache_hit_rate,
                "error_rate": error_rate,
            }


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    return _metrics_collector


@router.get("/metrics", response_model=Metrics, tags=["Monitoring"])
async def get_metrics():
    """
    Get service performance metrics.

    Provides comprehensive metrics for monitoring service health and performance:

    **Request Statistics**:
    - Total requests processed since startup
    - Requests in last hour
    - Current request rate (requests per minute)

    **Latency Statistics**:
    - Average inference time
    - P50, P95, P99 latency percentiles

    **Resource Utilization**:
    - GPU utilization percentage (if available)
    - VRAM usage percentage
    - Model cache hit rate

    **Error Statistics**:
    - Error rate (errors / total requests)

    **Use Cases**:
    - Production monitoring dashboards
    - Alerting on performance degradation
    - Capacity planning
    - SLA compliance tracking

    **Example Response**:
    ```json
    {
      "requests_total": 1523,
      "requests_last_hour": 45,
      "requests_per_minute": 0.75,
      "avg_inference_time_ms": 2156.3,
      "p50_inference_time_ms": 1800.0,
      "p95_inference_time_ms": 4200.0,
      "p99_inference_time_ms": 8500.0,
      "gpu_utilization_percent": 72.5,
      "vram_usage_percent": 45.2,
      "cache_hit_rate": 0.67,
      "error_rate": 0.02
    }
    ```

    **Returns**:
    - Current service metrics
    """
    metrics_data = _metrics_collector.get_metrics()
    return Metrics(**metrics_data)
