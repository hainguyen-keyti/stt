"""
ASR Engine Factory

Provides factory pattern for creating ASR engine instances.
"""

import logging
from typing import Type

from lib.engines.base import ASREngine
from lib.engines.faster_whisper import FasterWhisperEngine, FASTER_WHISPER_AVAILABLE
from lib.engines.openai_whisper import OpenAIWhisperEngine, OPENAI_WHISPER_AVAILABLE

logger = logging.getLogger(__name__)


class EngineFactory:
    """
    Factory for creating ASR engine instances.

    Handles engine availability checking and provides clear error messages.
    """

    # Registry of available engines
    _engines = {
        "faster-whisper": (FasterWhisperEngine, FASTER_WHISPER_AVAILABLE),
        "openai-whisper": (OpenAIWhisperEngine, OPENAI_WHISPER_AVAILABLE),
    }

    @classmethod
    def create_engine(cls, engine_name: str) -> ASREngine:
        """
        Create an ASR engine instance by name.

        Args:
            engine_name: Engine name ("faster-whisper", "openai-whisper")

        Returns:
            ASREngine instance

        Raises:
            ValueError: If engine name is unknown or unavailable
        """
        engine_name = engine_name.lower()

        # Check if engine is registered
        if engine_name not in cls._engines:
            available = ", ".join(cls._engines.keys())
            raise ValueError(
                f"Unsupported engine: '{engine_name}'. "
                f"Available engines: {available}"
            )

        # Get engine class and availability
        engine_class, is_available = cls._engines[engine_name]

        # Check if engine is available (dependencies installed)
        if not is_available:
            raise ValueError(
                f"Engine '{engine_name}' is not available. "
                f"Please install required dependencies."
            )

        # Create and return engine instance
        logger.info(f"Creating engine: {engine_name}")
        return engine_class()

    @classmethod
    def get_available_engines(cls) -> list[str]:
        """
        Get list of available engine names.

        Returns:
            List of engine names that are currently available
        """
        return [
            name
            for name, (_, is_available) in cls._engines.items()
            if is_available
        ]

    @classmethod
    def is_engine_available(cls, engine_name: str) -> bool:
        """
        Check if a specific engine is available.

        Args:
            engine_name: Engine name to check

        Returns:
            True if engine is available, False otherwise
        """
        engine_name = engine_name.lower()
        if engine_name not in cls._engines:
            return False
        _, is_available = cls._engines[engine_name]
        return is_available


def get_engine(engine_name: str) -> ASREngine:
    """
    Convenience function to create an engine instance.

    Args:
        engine_name: Engine name

    Returns:
        ASREngine instance
    """
    return EngineFactory.create_engine(engine_name)
