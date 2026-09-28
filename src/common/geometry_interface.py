"""
The swappable AI Geometry Module contract (ARCHITECTURE.md, CLAUDE.md hard constraint #1).

Every geometry-estimation backend — COLMAP (default/fallback) or any future AI model
(VGGT etc., Phase 9 stretch) — implements this single interface. Nothing downstream of
`estimate_geometry()` may depend on which backend produced its output. This is the only
file that should ever need to know backend-specific details; the rest of the pipeline
(scale/geo alignment, meshing, class tagging, confidence reporting) works purely off
`GeometryEstimate`.

**Never wire a caller directly to a specific backend class.** Callers get a backend via
`get_geometry_backend()` and call `.estimate_geometry(frames)` — that's the whole contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from common.coordinate_frames import CoordinateFrame


@dataclass
class CameraPose:
    frame_path: str
    rotation: np.ndarray      # (3,3) world-to-camera rotation
    translation: np.ndarray   # (3,) world-to-camera translation
    intrinsics: np.ndarray    # (3,3) camera intrinsic matrix
    coordinate_frame: CoordinateFrame = CoordinateFrame.SFM

    @property
    def camera_center(self) -> np.ndarray:
        """Physical camera center in world coordinates: C = -R^T @ t."""
        return -self.rotation.T @ self.translation


@dataclass
class GeometryEstimate:
    """The single output contract every backend must produce."""
    poses: list[CameraPose]
    points_xyz: np.ndarray        # (N, 3) sparse or dense point cloud, arbitrary scale
    points_rgb: np.ndarray | None  # (N, 3) uint8 color, if available
    points_confidence: np.ndarray | None  # (N,) per-point confidence/observation count
    backend_name: str
    is_metric_scale: bool          # False until Scale+Geo Alignment (Phase 3) runs
    coordinate_frame: CoordinateFrame = CoordinateFrame.SFM


class GeometryBackend(Protocol):
    """Anything satisfying this satisfies the contract — COLMAP or a future AI model."""

    name: str

    def estimate_geometry(self, frame_paths: list[str], work_dir: str | Path) -> GeometryEstimate:
        ...


def get_geometry_backend(name: str = "colmap") -> GeometryBackend:
    """The single place that knows concrete backend classes exist.

    Default is COLMAP, per CLAUDE.md hard constraint #1: COLMAP must remain the default
    path with no AI geometry model as a hard dependency. Any other backend name must be
    explicitly requested by the caller — never silently substituted.
    """
    if name == "colmap":
        from reconstruction.colmap_backend import ColmapBackend

        return ColmapBackend()
    if name == "vggt":
        raise NotImplementedError(
            "VGGT backend is a Phase 9 stretch goal (not yet implemented) — "
            "COLMAP remains the only available backend. See ARCHITECTURE.md."
        )
    raise ValueError(f"Unknown geometry backend: {name!r}")
