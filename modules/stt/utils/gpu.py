"""
GPU Detection and VRAM Utilities

Provides utilities for detecting GPU availability, monitoring VRAM usage,
and managing compute resources.
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Try to import torch, handle gracefully if not available
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - GPU features disabled")


def is_gpu_available() -> bool:
    """
    Check if GPU (CUDA) is available for computation.

    Returns:
        bool: True if CUDA GPU is available, False otherwise
    """
    if not TORCH_AVAILABLE:
        return False

    return torch.cuda.is_available()


def get_gpu_info() -> Dict[str, Any]:
    """
    Get detailed GPU information.

    Returns:
        Dict with GPU details including:
        - available: bool - Whether GPU is available
        - device_count: int - Number of GPUs
        - device_name: str - Name of primary GPU (if available)
        - cuda_version: str - CUDA version (if available)
    """
    info = {
        "available": False,
        "device_count": 0,
        "device_name": None,
        "cuda_version": None,
    }

    if not TORCH_AVAILABLE:
        return info

    if torch.cuda.is_available():
        info["available"] = True
        info["device_count"] = torch.cuda.device_count()
        if info["device_count"] > 0:
            info["device_name"] = torch.cuda.get_device_name(0)
        info["cuda_version"] = torch.version.cuda

    return info


def get_vram_info(device_index: int = 0) -> Dict[str, float]:
    """
    Get VRAM usage information for specified GPU device.

    Args:
        device_index: GPU device index (default: 0)

    Returns:
        Dict with VRAM details in MB:
        - total_mb: Total VRAM
        - allocated_mb: Currently allocated VRAM
        - reserved_mb: Currently reserved VRAM
        - free_mb: Available VRAM
        - usage_percent: Percentage of VRAM in use
    """
    if not TORCH_AVAILABLE or not torch.cuda.is_available():
        return {
            "total_mb": 0,
            "allocated_mb": 0,
            "reserved_mb": 0,
            "free_mb": 0,
            "usage_percent": 0.0,
        }

    try:
        # Get memory stats in bytes, convert to MB
        total = torch.cuda.get_device_properties(device_index).total_memory / (1024**2)
        allocated = torch.cuda.memory_allocated(device_index) / (1024**2)
        reserved = torch.cuda.memory_reserved(device_index) / (1024**2)
        free = total - allocated

        usage_percent = (allocated / total * 100) if total > 0 else 0.0

        return {
            "total_mb": round(total, 2),
            "allocated_mb": round(allocated, 2),
            "reserved_mb": round(reserved, 2),
            "free_mb": round(free, 2),
            "usage_percent": round(usage_percent, 2),
        }
    except Exception as e:
        logger.error(f"Error getting VRAM info: {e}")
        return {
            "total_mb": 0,
            "allocated_mb": 0,
            "reserved_mb": 0,
            "free_mb": 0,
            "usage_percent": 0.0,
        }


def get_optimal_device() -> str:
    """
    Get the optimal device string for PyTorch operations.

    Returns:
        str: "cuda" if GPU available, "cpu" otherwise
    """
    return "cuda" if is_gpu_available() else "cpu"


def get_optimal_compute_type() -> str:
    """
    Get optimal compute type based on hardware availability.

    For faster-whisper:
    - GPU available: "float16" (faster, uses less VRAM)
    - CPU only: "int8" (fastest on CPU)

    Returns:
        str: Recommended compute type ("float16", "int8", etc.)
    """
    if is_gpu_available():
        return "float16"
    else:
        return "int8"


def check_vram_availability(required_mb: float, device_index: int = 0) -> bool:
    """
    Check if sufficient VRAM is available for an operation.

    Args:
        required_mb: Required VRAM in megabytes
        device_index: GPU device index

    Returns:
        bool: True if sufficient VRAM available
    """
    if not is_gpu_available():
        return False

    vram = get_vram_info(device_index)
    return vram["free_mb"] >= required_mb


def clear_gpu_cache():
    """
    Clear PyTorch CUDA cache to free up VRAM.

    Should be called after unloading models or when VRAM is running low.
    """
    if TORCH_AVAILABLE and torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info("GPU cache cleared")
