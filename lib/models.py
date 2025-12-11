"""
Model Manager with Caching and VRAM Monitoring

Manages ASR model lifecycle including loading, caching, and automatic cleanup
when VRAM usage exceeds thresholds.
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from collections import OrderedDict

from lib.engines.base import ASREngine
from lib.engines.factory import EngineFactory
from lib.utils.gpu import get_vram_info, clear_gpu_cache, is_gpu_available

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages ASR model loading, caching, and lifecycle.

    Features:
    - LRU cache for loaded models
    - VRAM monitoring and automatic cleanup
    - Lazy loading (models loaded on first use)
    - Resource tracking
    """

    def __init__(self, vram_limit_percent: float = 80.0, max_cached_models: int = 3):
        """
        Initialize the model manager.

        Args:
            vram_limit_percent: Maximum VRAM usage percent before cleanup (default: 80%)
            max_cached_models: Maximum number of models to keep cached (default: 3)
        """
        self.vram_limit_percent = vram_limit_percent
        self.max_cached_models = max_cached_models

        # LRU cache: (engine_name, model_size) -> (engine_instance, load_time, vram_mb)
        self._cache: OrderedDict[Tuple[str, str], Tuple[ASREngine, datetime, Optional[float]]] = OrderedDict()

        logger.info(
            "ModelManager initialized",
            extra={
                "metadata": {
                    "vram_limit_percent": vram_limit_percent,
                    "max_cached_models": max_cached_models,
                }
            },
        )

    def get_engine(
        self, engine_name: str, model_size: str, config: dict
    ) -> ASREngine:
        """
        Get or load an ASR engine instance.

        Implements lazy loading - models are loaded only when first requested.
        Uses LRU cache to avoid redundant loading.

        Args:
            engine_name: Engine identifier ("faster-whisper", "openai-whisper")
            model_size: Model size to load
            config: Engine configuration dict

        Returns:
            ASREngine: Loaded engine instance

        Raises:
            ValueError: If engine name is not supported
            Exception: If model loading fails
        """
        cache_key = (engine_name, model_size)

        # Check cache
        if cache_key in self._cache:
            logger.info(
                f"Model cache hit: {engine_name}/{model_size}",
                extra={"metadata": {"engine": engine_name, "model_size": model_size}},
            )

            # Move to end (most recently used)
            engine, load_time, vram_mb = self._cache.pop(cache_key)
            self._cache[cache_key] = (engine, load_time, vram_mb)

            return engine

        # Cache miss - need to load model
        logger.info(
            f"Model cache miss: {engine_name}/{model_size}",
            extra={"metadata": {"engine": engine_name, "model_size": model_size}},
        )

        # Check VRAM before loading
        self._check_and_cleanup_vram()

        # Create engine instance
        engine = self._create_engine(engine_name)

        # Record VRAM before loading
        vram_before = None
        if is_gpu_available():
            vram_before = get_vram_info()["allocated_mb"]

        # Load model
        load_start = datetime.now()
        engine.load_model(model_size, config)
        load_time = datetime.now()

        # Record VRAM after loading
        vram_used = None
        if is_gpu_available() and vram_before is not None:
            vram_after = get_vram_info()["allocated_mb"]
            vram_used = vram_after - vram_before

        # Add to cache
        self._cache[cache_key] = (engine, load_time, vram_used)

        # Enforce max cache size
        if len(self._cache) > self.max_cached_models:
            self._evict_lru()

        logger.info(
            f"Model loaded and cached: {engine_name}/{model_size}",
            extra={
                "metadata": {
                    "engine": engine_name,
                    "model_size": model_size,
                    "vram_used_mb": vram_used,
                    "cache_size": len(self._cache),
                }
            },
        )

        return engine

    def _create_engine(self, engine_name: str) -> ASREngine:
        """
        Create an engine instance using the EngineFactory.

        Args:
            engine_name: Engine identifier

        Returns:
            ASREngine: Unloaded engine instance

        Raises:
            ValueError: If engine name is not supported
        """
        return EngineFactory.create_engine(engine_name)

    def _check_and_cleanup_vram(self):
        """
        Check VRAM usage and cleanup if necessary.

        If VRAM usage exceeds the limit, evict cached models until
        usage drops below threshold.
        """
        if not is_gpu_available():
            return

        vram_info = get_vram_info()
        current_usage = vram_info["usage_percent"]

        if current_usage >= self.vram_limit_percent:
            logger.warning(
                f"VRAM usage {current_usage:.1f}% exceeds limit {self.vram_limit_percent}%",
                extra={
                    "metadata": {
                        "vram_usage_percent": current_usage,
                        "vram_limit_percent": self.vram_limit_percent,
                    }
                },
            )

            # Evict models until usage drops
            while current_usage >= self.vram_limit_percent and len(self._cache) > 0:
                self._evict_lru()
                clear_gpu_cache()

                vram_info = get_vram_info()
                current_usage = vram_info["usage_percent"]

                logger.info(
                    f"VRAM usage after cleanup: {current_usage:.1f}%",
                    extra={"metadata": {"vram_usage_percent": current_usage}},
                )

    def _evict_lru(self):
        """
        Evict the least recently used model from cache.
        """
        if len(self._cache) == 0:
            return

        # Remove oldest (LRU) entry
        cache_key, (engine, load_time, vram_mb) = self._cache.popitem(last=False)
        engine_name, model_size = cache_key

        logger.info(
            f"Evicted model from cache: {engine_name}/{model_size}",
            extra={
                "metadata": {
                    "engine": engine_name,
                    "model_size": model_size,
                    "vram_mb": vram_mb,
                }
            },
        )

        # Note: Python's garbage collector will handle cleanup
        # The model object will be freed when no longer referenced

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache information:
            - cached_models: Number of models in cache
            - cache_keys: List of cached (engine, model_size) tuples
            - total_vram_mb: Total VRAM used by cached models
        """
        total_vram = sum(
            vram_mb for _, _, vram_mb in self._cache.values() if vram_mb is not None
        )

        return {
            "cached_models": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "total_vram_mb": round(total_vram, 2) if total_vram else 0.0,
        }

    def clear_cache(self):
        """
        Clear all cached models.

        Useful for freeing memory or forcing model reload.
        """
        cache_size = len(self._cache)
        self._cache.clear()

        if is_gpu_available():
            clear_gpu_cache()

        logger.info(
            f"Model cache cleared ({cache_size} models removed)",
            extra={"metadata": {"models_cleared": cache_size}},
        )

    def list_loaded_models(self) -> list:
        """
        List all currently loaded models.

        Returns:
            List of dicts with model information
        """
        models = []
        for (engine_name, model_size), (engine, load_time, vram_mb) in self._cache.items():
            models.append({
                "engine": engine_name,
                "model_size": model_size,
                "load_time": load_time.isoformat(),
                "vram_mb": vram_mb,
            })

        return models


# Global model manager instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """
    Get the global ModelManager instance.

    Implements singleton pattern for model management.

    Returns:
        ModelManager: Global model manager instance
    """
    global _model_manager

    if _model_manager is None:
        _model_manager = ModelManager()

    return _model_manager
