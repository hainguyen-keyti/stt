"""
Hardware Detection and Resource Utilities

Provides utilities for detecting available hardware (CUDA, MPS, ROCm, CPU),
monitoring memory usage, and managing compute resources across all platforms.

Supported platforms:
- NVIDIA CUDA (Linux, Windows)
- Apple Silicon MPS (macOS M1/M2/M3/M4)
- AMD ROCm (Linux)
- CPU fallback (all platforms)
"""

from typing import Optional, Dict, Any, Tuple
from enum import Enum
import logging
import platform
import os

logger = logging.getLogger(__name__)

# Try to import torch, handle gracefully if not available
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - GPU features disabled")


class DeviceType(Enum):
    """Supported device types for computation."""
    CUDA = "cuda"      # NVIDIA GPU
    MPS = "mps"        # Apple Silicon
    ROCM = "rocm"      # AMD GPU (uses cuda backend in PyTorch)
    CPU = "cpu"        # CPU fallback


def get_system_info() -> Dict[str, Any]:
    """
    Get system information for hardware detection.

    Returns:
        Dict with system details including OS, architecture, etc.
    """
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def is_cuda_available() -> bool:
    """Check if NVIDIA CUDA is available."""
    if not TORCH_AVAILABLE:
        return False
    return torch.cuda.is_available()


def is_mps_available() -> bool:
    """Check if Apple Silicon MPS is available."""
    if not TORCH_AVAILABLE:
        return False

    # MPS is only available on macOS with Apple Silicon
    if platform.system() != "Darwin":
        return False

    try:
        return torch.backends.mps.is_available() and torch.backends.mps.is_built()
    except AttributeError:
        # Older PyTorch versions don't have MPS support
        return False


def is_rocm_available() -> bool:
    """Check if AMD ROCm is available."""
    if not TORCH_AVAILABLE:
        return False

    # ROCm uses CUDA API in PyTorch, check for AMD GPU
    if torch.cuda.is_available():
        try:
            device_name = torch.cuda.get_device_name(0).lower()
            # AMD GPUs typically have "amd" or "radeon" in the name
            return "amd" in device_name or "radeon" in device_name
        except Exception:
            pass

    # Alternative: check for ROCm environment variable
    return os.environ.get("ROCM_HOME") is not None or os.environ.get("HIP_PATH") is not None


def is_gpu_available() -> bool:
    """
    Check if any GPU (CUDA, MPS, or ROCm) is available for computation.

    Returns:
        bool: True if any GPU is available, False otherwise
    """
    return is_cuda_available() or is_mps_available() or is_rocm_available()


def get_available_devices() -> Dict[str, bool]:
    """
    Get availability status of all device types.

    Returns:
        Dict with device availability status
    """
    return {
        "cuda": is_cuda_available(),
        "mps": is_mps_available(),
        "rocm": is_rocm_available(),
        "cpu": True,  # CPU is always available
    }


def get_device_priority() -> list:
    """
    Get device priority order based on typical performance.

    Returns:
        List of device types in priority order
    """
    # CUDA/ROCm typically faster than MPS for ML workloads
    return [DeviceType.CUDA, DeviceType.ROCM, DeviceType.MPS, DeviceType.CPU]


def get_optimal_device() -> str:
    """
    Get the optimal device string for PyTorch operations.

    Priority: CUDA > ROCm > MPS > CPU

    Returns:
        str: Device string ("cuda", "mps", or "cpu")
    """
    if is_cuda_available():
        if is_rocm_available():
            logger.info("AMD ROCm GPU detected, using CUDA backend")
        else:
            logger.info("NVIDIA CUDA GPU detected")
        return "cuda"

    if is_mps_available():
        logger.info("Apple Silicon MPS detected")
        return "mps"

    logger.info("No GPU detected, using CPU")
    return "cpu"


def get_optimal_compute_type(device: str = None) -> str:
    """
    Get optimal compute type based on hardware availability.

    For faster-whisper and other models:
    - CUDA GPU: "float16" (faster, uses less VRAM)
    - MPS (Apple Silicon): "float16" (optimized for M-series)
    - CPU: "int8" (fastest on CPU)

    Args:
        device: Optional device override. If None, auto-detects.

    Returns:
        str: Recommended compute type ("float16", "int8", etc.)
    """
    if device is None:
        device = get_optimal_device()

    if device in ("cuda", "mps"):
        return "float16"
    else:
        return "int8"


def get_gpu_info() -> Dict[str, Any]:
    """
    Get detailed GPU/accelerator information.

    Returns:
        Dict with GPU details including:
        - available: bool - Whether GPU is available
        - device_type: str - Type of device (cuda, mps, cpu)
        - device_count: int - Number of GPUs
        - device_name: str - Name of primary GPU (if available)
        - cuda_version: str - CUDA version (if available)
        - mps_available: bool - MPS availability
        - driver_version: str - Driver version (if available)
    """
    info = {
        "available": False,
        "device_type": "cpu",
        "device_count": 0,
        "device_name": None,
        "cuda_version": None,
        "mps_available": False,
        "rocm_available": False,
        "driver_version": None,
        "torch_version": None,
    }

    if not TORCH_AVAILABLE:
        return info

    info["torch_version"] = torch.__version__

    # Check CUDA (NVIDIA or AMD ROCm)
    if torch.cuda.is_available():
        info["available"] = True
        info["device_count"] = torch.cuda.device_count()

        if info["device_count"] > 0:
            info["device_name"] = torch.cuda.get_device_name(0)

            # Detect if it's AMD ROCm
            if is_rocm_available():
                info["device_type"] = "rocm"
                info["rocm_available"] = True
            else:
                info["device_type"] = "cuda"
                info["cuda_version"] = torch.version.cuda

                # Try to get driver version
                try:
                    import subprocess
                    result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        info["driver_version"] = result.stdout.strip().split('\n')[0]
                except Exception:
                    pass

    # Check MPS (Apple Silicon)
    elif is_mps_available():
        info["available"] = True
        info["device_type"] = "mps"
        info["mps_available"] = True
        info["device_count"] = 1

        # Get Apple Silicon chip info
        try:
            import subprocess
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info["device_name"] = result.stdout.strip()
        except Exception:
            info["device_name"] = "Apple Silicon"

    return info


def get_vram_info(device_index: int = 0) -> Dict[str, float]:
    """
    Get VRAM/memory usage information for the current accelerator.

    Args:
        device_index: GPU device index (default: 0)

    Returns:
        Dict with memory details in MB:
        - total_mb: Total memory
        - allocated_mb: Currently allocated memory
        - reserved_mb: Currently reserved memory
        - free_mb: Available memory
        - usage_percent: Percentage of memory in use
        - device_type: Type of device being reported
    """
    default_info = {
        "total_mb": 0,
        "allocated_mb": 0,
        "reserved_mb": 0,
        "free_mb": 0,
        "usage_percent": 0.0,
        "device_type": "cpu",
    }

    if not TORCH_AVAILABLE:
        return default_info

    # CUDA memory info
    if torch.cuda.is_available():
        try:
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
                "device_type": "cuda" if not is_rocm_available() else "rocm",
            }
        except Exception as e:
            logger.error(f"Error getting CUDA VRAM info: {e}")
            return default_info

    # MPS memory info (Apple Silicon)
    if is_mps_available():
        try:
            # MPS doesn't have direct memory query API like CUDA
            # We can get allocated memory but not total
            allocated = torch.mps.current_allocated_memory() / (1024**2)

            # Try to get system memory as reference
            try:
                import subprocess
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    # Apple Silicon shares memory between CPU and GPU
                    # Unified memory, so we report system memory
                    total = int(result.stdout.strip()) / (1024**2)
                else:
                    total = 0
            except Exception:
                total = 0

            free = total - allocated if total > 0 else 0
            usage_percent = (allocated / total * 100) if total > 0 else 0.0

            return {
                "total_mb": round(total, 2),
                "allocated_mb": round(allocated, 2),
                "reserved_mb": round(allocated, 2),  # MPS doesn't differentiate
                "free_mb": round(free, 2),
                "usage_percent": round(usage_percent, 2),
                "device_type": "mps",
            }
        except Exception as e:
            logger.error(f"Error getting MPS memory info: {e}")
            return default_info

    return default_info


def check_vram_availability(required_mb: float, device_index: int = 0) -> bool:
    """
    Check if sufficient VRAM/memory is available for an operation.

    Args:
        required_mb: Required memory in megabytes
        device_index: GPU device index

    Returns:
        bool: True if sufficient memory available
    """
    if not is_gpu_available():
        return False

    vram = get_vram_info(device_index)
    return vram["free_mb"] >= required_mb


def clear_gpu_cache():
    """
    Clear GPU cache to free up memory.

    Works with CUDA, ROCm, and MPS backends.
    Should be called after unloading models or when memory is running low.
    """
    if not TORCH_AVAILABLE:
        return

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        logger.info("CUDA cache cleared")

    if is_mps_available():
        try:
            torch.mps.empty_cache()
            logger.info("MPS cache cleared")
        except Exception as e:
            logger.debug(f"MPS cache clear not available: {e}")


def get_recommended_batch_size(model_size: str = "base") -> int:
    """
    Get recommended batch size based on available hardware.

    Args:
        model_size: Whisper model size (tiny, base, small, medium, large)

    Returns:
        Recommended batch size for the hardware
    """
    # Model VRAM requirements (approximate, in MB)
    model_vram = {
        "tiny": 1000,
        "base": 1500,
        "small": 2500,
        "medium": 5000,
        "large": 10000,
        "large-v2": 10000,
        "large-v3": 10000,
    }

    vram = get_vram_info()
    free_mb = vram["free_mb"]
    required = model_vram.get(model_size, 2000)

    if free_mb <= 0:
        return 1  # CPU fallback

    # Calculate batch size based on available memory
    available_for_batch = free_mb - required
    if available_for_batch <= 0:
        return 1

    # Rough estimate: each additional batch item needs ~500MB
    batch_size = max(1, int(available_for_batch / 500))

    # Cap batch size based on device type
    device = get_optimal_device()
    if device == "mps":
        return min(batch_size, 8)  # MPS works best with smaller batches
    elif device == "cuda":
        return min(batch_size, 32)  # CUDA can handle larger batches
    else:
        return min(batch_size, 4)  # CPU


def get_num_workers() -> int:
    """
    Get optimal number of workers for data loading based on hardware.

    Returns:
        Recommended number of workers
    """
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()

    device = get_optimal_device()

    if device == "cuda":
        # For CUDA, use fewer workers to avoid CPU bottleneck
        return min(4, cpu_count)
    elif device == "mps":
        # MPS benefits from more workers due to unified memory
        return min(cpu_count, 8)
    else:
        # CPU: use most cores but leave some for system
        return max(1, cpu_count - 2)


def get_cpu_info() -> Dict[str, Any]:
    """
    Get detailed CPU information.

    Returns:
        Dict with CPU details
    """
    import multiprocessing

    info = {
        "physical_cores": None,
        "logical_cores": multiprocessing.cpu_count(),
        "model": None,
        "frequency_mhz": None,
    }

    try:
        # Try to get physical core count
        import os
        if hasattr(os, 'sched_getaffinity'):
            info["physical_cores"] = len(os.sched_getaffinity(0))
    except Exception:
        pass

    # Get CPU model name
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            import subprocess
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info["model"] = result.stdout.strip()
        elif system == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        info["model"] = line.split(":")[1].strip()
                        break
        elif system == "Windows":
            import subprocess
            result = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    info["model"] = lines[1].strip()
    except Exception:
        pass

    return info


def get_memory_info() -> Dict[str, float]:
    """
    Get system RAM information.

    Returns:
        Dict with memory details in MB
    """
    info = {
        "total_mb": 0,
        "available_mb": 0,
        "used_mb": 0,
        "usage_percent": 0.0,
    }

    try:
        import psutil
        mem = psutil.virtual_memory()
        info["total_mb"] = round(mem.total / (1024**2), 2)
        info["available_mb"] = round(mem.available / (1024**2), 2)
        info["used_mb"] = round(mem.used / (1024**2), 2)
        info["usage_percent"] = round(mem.percent, 2)
    except ImportError:
        # psutil not available, try alternative methods
        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                import subprocess
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    info["total_mb"] = round(int(result.stdout.strip()) / (1024**2), 2)
            elif system == "Linux":
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            info["total_mb"] = round(int(line.split()[1]) / 1024, 2)
                        elif line.startswith("MemAvailable:"):
                            info["available_mb"] = round(int(line.split()[1]) / 1024, 2)
                    info["used_mb"] = info["total_mb"] - info["available_mb"]
                    if info["total_mb"] > 0:
                        info["usage_percent"] = round((info["used_mb"] / info["total_mb"]) * 100, 2)
        except Exception:
            pass

    return info


def get_disk_info(path: str = "/") -> Dict[str, float]:
    """
    Get disk space information.

    Args:
        path: Path to check disk space for

    Returns:
        Dict with disk details in GB
    """
    info = {
        "total_gb": 0,
        "free_gb": 0,
        "used_gb": 0,
        "usage_percent": 0.0,
    }

    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        info["total_gb"] = round(total / (1024**3), 2)
        info["used_gb"] = round(used / (1024**3), 2)
        info["free_gb"] = round(free / (1024**3), 2)
        if info["total_gb"] > 0:
            info["usage_percent"] = round((info["used_gb"] / info["total_gb"]) * 100, 2)
    except Exception:
        pass

    return info


def get_full_hardware_info() -> Dict[str, Any]:
    """
    Get comprehensive hardware information for benchmarking.

    Returns:
        Dict with all hardware details
    """
    return {
        "system": get_system_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "gpu": get_gpu_info(),
        "gpu_memory": get_vram_info() if is_gpu_available() else None,
        "optimal_config": {
            "device": get_optimal_device(),
            "compute_type": get_optimal_compute_type(),
            "num_workers": get_num_workers(),
        },
    }


def print_hardware_summary():
    """Print a comprehensive summary of available hardware to the logger."""
    info = get_gpu_info()
    system = get_system_info()
    cpu = get_cpu_info()
    memory = get_memory_info()
    disk = get_disk_info()

    logger.info("=" * 60)
    logger.info("HARDWARE DETECTION SUMMARY")
    logger.info("=" * 60)

    # System Info
    logger.info(f"OS: {system['os']} {system.get('os_version', '')} ({system['architecture']})")
    logger.info(f"Python: {system['python_version']}")
    logger.info(f"PyTorch: {info.get('torch_version', 'N/A')}")

    logger.info("-" * 60)

    # CPU Info
    logger.info("CPU:")
    if cpu.get("model"):
        logger.info(f"  Model: {cpu['model']}")
    logger.info(f"  Cores: {cpu.get('physical_cores') or cpu['logical_cores']} physical, {cpu['logical_cores']} logical")

    # Memory Info
    logger.info("RAM:")
    logger.info(f"  Total: {memory['total_mb']:.0f} MB ({memory['total_mb']/1024:.1f} GB)")
    logger.info(f"  Available: {memory['available_mb']:.0f} MB ({memory['usage_percent']:.1f}% used)")

    # Disk Info
    logger.info("Disk:")
    logger.info(f"  Total: {disk['total_gb']:.1f} GB")
    logger.info(f"  Free: {disk['free_gb']:.1f} GB ({disk['usage_percent']:.1f}% used)")

    logger.info("-" * 60)

    # GPU Info
    if info["available"]:
        logger.info(f"GPU: {info['device_type'].upper()}")
        logger.info(f"  Device: {info['device_name']}")
        logger.info(f"  Count: {info['device_count']}")

        if info['cuda_version']:
            logger.info(f"  CUDA: {info['cuda_version']}")
        if info['driver_version']:
            logger.info(f"  Driver: {info['driver_version']}")

        vram = get_vram_info()
        if vram['total_mb'] > 0:
            logger.info(f"  VRAM: {vram['total_mb']:.0f} MB total, {vram['free_mb']:.0f} MB free ({vram['usage_percent']:.1f}% used)")
    else:
        logger.info("GPU: None detected (using CPU)")

    logger.info("-" * 60)

    # Optimal Configuration
    logger.info("OPTIMAL CONFIGURATION:")
    logger.info(f"  Device: {get_optimal_device()}")
    logger.info(f"  Compute Type: {get_optimal_compute_type()}")
    logger.info(f"  Workers: {get_num_workers()}")

    logger.info("=" * 60)
