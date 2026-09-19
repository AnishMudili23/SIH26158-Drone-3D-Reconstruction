"""
Phase 0 — GPU capability check.

Answers: what CUDA/VRAM do we actually have, and what does that mean for
which model sizes (Depth Anything V2 checkpoints, COLMAP dense MVS, etc.)
are realistic on this machine, per CLAUDE.md's 6GB VRAM hard constraint.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass
class GpuReport:
    cuda_available: bool
    device_name: str | None
    total_vram_mb: float | None
    driver_version: str | None
    cuda_runtime_version: str | None
    torch_version: str | None
    recommendation: str


def _nvidia_smi_driver_version() -> str | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            text=True,
            timeout=10,
        )
        return out.strip().splitlines()[0]
    except Exception:
        return None


def run_gpu_check() -> GpuReport:
    try:
        import torch
    except ImportError:
        return GpuReport(
            cuda_available=False,
            device_name=None,
            total_vram_mb=None,
            driver_version=_nvidia_smi_driver_version(),
            cuda_runtime_version=None,
            torch_version=None,
            recommendation=(
                "PyTorch not installed — cannot confirm CUDA path. "
                "CPU-only fallback assumed until torch is available."
            ),
        )

    cuda_available = torch.cuda.is_available()
    device_name = None
    total_vram_mb = None
    cuda_runtime_version = torch.version.cuda

    if cuda_available:
        props = torch.cuda.get_device_properties(0)
        device_name = props.name
        total_vram_mb = props.total_memory / (1024 * 1024)

    # Recommendation logic tied directly to CLAUDE.md's hard constraint #2:
    # no pipeline stage may assume >6GB VRAM without an explicit fallback.
    if not cuda_available:
        recommendation = (
            "No CUDA device visible to PyTorch. Every GPU-accelerated stage "
            "(COLMAP dense MVS, Depth Anything V2) must fall back to CPU-only "
            "execution, which will be significantly slower but still correct."
        )
    elif total_vram_mb is not None and total_vram_mb < 5900:
        # Real GPUs always report a bit under their nominal size (a few MiB reserved
        # by the driver/OS) — a bare `< 6144` check flagged an actual 6GB card
        # (reported 6143.5 MiB) as "below target", which is wrong. Use a tolerance.
        recommendation = (
            f"Only {total_vram_mb:.0f}MiB VRAM detected — below the 6GB target. "
            "Use the smallest available checkpoints (Depth Anything V2 'small') "
            "and process frames in smaller batches."
        )
    else:
        recommendation = (
            f"{total_vram_mb:.0f}MiB VRAM confirmed (RTX 3050 class). "
            "Depth Anything V2 small/base checkpoints fit comfortably. "
            "COLMAP dense MVS (patch-match stereo) will run on GPU but should "
            "process frames in batches for large sequences to stay within budget. "
            "VGGT (Phase 9, stretch) is NOT safe to run locally at full frame "
            "counts on this VRAM budget — route heavy VGGT runs to a free-tier "
            "cloud GPU (Colab/Kaggle T4) per ARCHITECTURE.md, never as a hard "
            "local dependency."
        )

    return GpuReport(
        cuda_available=cuda_available,
        device_name=device_name,
        total_vram_mb=total_vram_mb,
        driver_version=_nvidia_smi_driver_version(),
        cuda_runtime_version=cuda_runtime_version,
        torch_version=torch.__version__,
        recommendation=recommendation,
    )


if __name__ == "__main__":
    report = run_gpu_check()
    print(json.dumps(asdict(report), indent=2))
    sys.exit(0 if report.cuda_available else 1)
