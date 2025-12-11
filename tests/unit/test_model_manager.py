"""
Unit tests for ModelManager

Tests model caching, VRAM monitoring, and resource management.
"""

import pytest
from lib.models import ModelManager, get_model_manager
from lib.engines.faster_whisper import FASTER_WHISPER_AVAILABLE


class TestModelManager:
    """Test suite for ModelManager"""

    def test_manager_creation(self):
        """Test ModelManager instantiation"""
        manager = ModelManager(vram_limit_percent=80.0, max_cached_models=3)

        assert manager is not None
        assert manager.vram_limit_percent == 80.0
        assert manager.max_cached_models == 3
        assert len(manager._cache) == 0

    def test_get_model_manager_singleton(self):
        """Test that get_model_manager returns singleton"""
        manager1 = get_model_manager()
        manager2 = get_model_manager()

        assert manager1 is manager2

    @pytest.mark.slow
    def test_cache_hit_avoids_reload(self):
        """Test that cached models are reused"""
        if not FASTER_WHISPER_AVAILABLE:
            pytest.skip("faster-whisper not available")

        manager = ModelManager()
        config = {"device": "cpu", "compute_type": "int8"}

        # First load
        engine1 = manager.get_engine("faster-whisper", "tiny", config)
        cache_stats1 = manager.get_cache_stats()

        # Second load (should hit cache)
        engine2 = manager.get_engine("faster-whisper", "tiny", config)
        cache_stats2 = manager.get_cache_stats()

        assert engine1 is engine2  # Same instance
        assert cache_stats1["cached_models"] == 1
        assert cache_stats2["cached_models"] == 1

    def test_unsupported_engine_raises_error(self):
        """Test that unsupported engine name raises error"""
        manager = ModelManager()

        with pytest.raises(ValueError, match="Unsupported engine"):
            manager.get_engine("fake-engine", "base", {})

    def test_cache_stats(self):
        """Test cache statistics retrieval"""
        manager = ModelManager()
        stats = manager.get_cache_stats()

        assert "cached_models" in stats
        assert "cache_keys" in stats
        assert "total_vram_mb" in stats
        assert stats["cached_models"] == 0

    def test_clear_cache(self):
        """Test cache clearing"""
        manager = ModelManager()

        # Initially empty
        assert manager.get_cache_stats()["cached_models"] == 0

        # Clear (should not error even when empty)
        manager.clear_cache()

        assert manager.get_cache_stats()["cached_models"] == 0

    def test_list_loaded_models(self):
        """Test listing loaded models"""
        manager = ModelManager()
        models = manager.list_loaded_models()

        assert isinstance(models, list)
        assert len(models) == 0

    @pytest.mark.slow
    def test_lru_eviction(self):
        """Test LRU eviction when cache exceeds max size"""
        if not FASTER_WHISPER_AVAILABLE:
            pytest.skip("faster-whisper not available")

        # Create manager with max 2 models
        manager = ModelManager(max_cached_models=2)
        config = {"device": "cpu", "compute_type": "int8"}

        # Load 3 different models (should evict oldest)
        manager.get_engine("faster-whisper", "tiny", config)
        manager.get_engine("faster-whisper", "base", config)
        manager.get_engine("faster-whisper", "small", config)

        # Should only have 2 models cached
        stats = manager.get_cache_stats()
        assert stats["cached_models"] == 2
