"""
Phase 7 / GIS Deliverable — Standard Classified Point Cloud Export (.LAS / .LAZ)
(Per SIH26158 guidelines and PRD.md: standard GIS deliverables include classified
point clouds adhering to ASPRS standards alongside PLY/GLB).

Maps semantic segmentation classes (UAVid taxonomy) to standard ASPRS LiDAR
classification codes:
  - Building (0)        -> ASPRS Class 6  (Building)
  - Road (1)            -> ASPRS Class 11 (Road Surface)
  - Tree (2)            -> ASPRS Class 5  (High Vegetation)
  - Low vegetation (3)  -> ASPRS Class 3  (Low Vegetation)
  - Moving car (4)      -> ASPRS Class 64 (Vehicle / User Defined)
  - Static car (5)      -> ASPRS Class 64 (Vehicle / User Defined)
  - Human (6)           -> ASPRS Class 1  (Unclassified)
  - Background (7)      -> ASPRS Class 1  (Unclassified)

Point Format 3 (LAS 1.4) is used to preserve XYZ, 16-bit RGB, intensity,
and standard classification codes with millimeter coordinate precision.
Supports both uncompressed (.las) and compressed (.laz) formats.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import laspy
import pyproj


# UAVid class ID -> ASPRS standard classification code
UAVID_TO_ASPRS: dict[int, int] = {
    0: 6,   # Building
    1: 11,  # Road Surface
    2: 5,   # High Vegetation
    3: 3,   # Low Vegetation
    4: 64,  # Moving Car -> Vehicle
    5: 64,  # Static Car -> Vehicle
    6: 1,   # Human -> Unclassified
    7: 1,   # Background clutter -> Unclassified
}


def export_point_cloud_to_las(
    points_xyz: np.ndarray,
    output_path: str | Path,
    points_rgb: np.ndarray | None = None,
    points_class: np.ndarray | None = None,
    points_confidence: np.ndarray | None = None,
    crs: pyproj.CRS | int | str | None = None,
    scale_precision: float = 0.001,
) -> Path:
    """Exports classified 3D points to a standard ASPRS .las or .laz file.

    Parameters
    ----------
    points_xyz : np.ndarray
        (N, 3) float array of 3D coordinates (metric / georeferenced).
    output_path : str | Path
        Target file path (.las or .laz).
    points_rgb : np.ndarray | None
        (N, 3) uint8 array of RGB colors (0-255).
    points_class : np.ndarray | None
        (N,) uint8 array of UAVid class IDs (0..7).
    points_confidence : np.ndarray | None
        (N,) float array of confidence / observations, stored in LAS intensity field.
    crs : pyproj.CRS | int | str | None
        Coordinate Reference System (EPSG integer, WKT string, or pyproj.CRS).
    scale_precision : float
        Grid precision in coordinate units (default 0.001 = 1mm).

    Returns
    -------
    Path
        Path to the written .las or .laz file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if points_xyz.ndim != 2 or points_xyz.shape[1] != 3:
        raise ValueError(f"points_xyz must have shape (N, 3), got {points_xyz.shape}")

    n_points = points_xyz.shape[0]

    # Use Point Format 7 (LAS 1.4 native: XYZ + RGB + Intensity + 8-bit Classification)
    header = laspy.LasHeader(point_format=7, version="1.4")

    if n_points > 0:
        min_coords = np.min(points_xyz, axis=0)
        header.offsets = [float(min_coords[0]), float(min_coords[1]), float(min_coords[2])]
    else:
        header.offsets = [0.0, 0.0, 0.0]

    header.scales = [scale_precision, scale_precision, scale_precision]

    if crs is not None:
        if isinstance(crs, int):
            proj_crs = pyproj.CRS.from_epsg(crs)
        elif isinstance(crs, str):
            proj_crs = pyproj.CRS.from_user_input(crs)
        else:
            proj_crs = crs
        header.add_crs(proj_crs)

    las = laspy.LasData(header)

    if n_points > 0:
        las.x = points_xyz[:, 0]
        las.y = points_xyz[:, 1]
        las.z = points_xyz[:, 2]

        if points_rgb is not None:
            if points_rgb.shape[0] != n_points or points_rgb.shape[1] != 3:
                raise ValueError("points_rgb must match points_xyz length and have 3 channels")
            # Scale 8-bit RGB (0-255) to 16-bit LAS RGB (0-65535)
            r8 = points_rgb[:, 0].astype(np.uint16)
            g8 = points_rgb[:, 1].astype(np.uint16)
            b8 = points_rgb[:, 2].astype(np.uint16)
            las.red = (r8 << 8) | r8
            las.green = (g8 << 8) | g8
            las.blue = (b8 << 8) | b8

        if points_class is not None:
            if points_class.shape[0] != n_points:
                raise ValueError("points_class must match points_xyz length")
            asprs_classes = np.array(
                [UAVID_TO_ASPRS.get(int(c), 1) for c in points_class], dtype=np.uint8
            )
            las.classification = asprs_classes
        else:
            las.classification = np.full(n_points, 1, dtype=np.uint8)  # Unclassified

        if points_confidence is not None:
            if points_confidence.shape[0] != n_points:
                raise ValueError("points_confidence must match points_xyz length")
            conf_min, conf_max = np.min(points_confidence), np.max(points_confidence)
            if conf_max > conf_min:
                normalized = (points_confidence - conf_min) / (conf_max - conf_min)
                las.intensity = (normalized * 65535).astype(np.uint16)
            else:
                las.intensity = np.full(n_points, 32768, dtype=np.uint16)

    las.write(str(output_path))
    return output_path
