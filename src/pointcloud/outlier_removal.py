"""
Outlier Removal — ARCHITECTURE.md's pipeline stage between point fusion and
scale/geo alignment: "statistical + radius filtering, Open3D".

Confirmed necessary by direct experiment, not just following the architecture doc on
faith: a real COLMAP sparse reconstruction's bounding box came out ~1000m x 900m for a
scene that is actually ~150m x 150m — a handful of weakly-triangulated outlier points
(a well-known SfM artifact, not a bug) were dominating any extent-based calculation
(DSM/DTM grid sizing, orthomosaic canvas sizing), producing a mostly-empty, absurdly
oversized raster. Statistical outlier removal fixes this at the source rather than
requiring every downstream consumer to defensively clip its own bounding box.
"""
from __future__ import annotations

import numpy as np
import open3d as o3d


def remove_statistical_outliers(
    points_xyz: np.ndarray,
    nb_neighbors: int = 20,
    std_ratio: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Open3D's statistical outlier removal: for each point, compute the mean distance
    to its `nb_neighbors` nearest neighbors; discard points whose mean distance is more
    than `std_ratio` standard deviations above the dataset's average mean-distance.

    Returns (kept_mask (N,) bool, kept_indices (K,) int) — kept_mask lets callers filter
    any parallel arrays (colors, confidence, class tags) consistently.
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_xyz)
    _, kept_indices = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)

    kept_mask = np.zeros(points_xyz.shape[0], dtype=bool)
    kept_mask[np.array(kept_indices)] = True
    return kept_mask, np.array(kept_indices)


def remove_radius_outliers(
    points_xyz: np.ndarray,
    nb_points: int = 8,
    radius: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Open3D's radius outlier removal: discard points with fewer than `nb_points`
    neighbors within `radius` — catches isolated points statistical removal can miss
    (e.g. small tight clusters of a few mutually-close outliers)."""
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_xyz)
    _, kept_indices = pcd.remove_radius_outlier(nb_points=nb_points, radius=radius)

    kept_mask = np.zeros(points_xyz.shape[0], dtype=bool)
    kept_mask[np.array(kept_indices)] = True
    return kept_mask, np.array(kept_indices)


def clean_point_cloud(
    points_xyz: np.ndarray,
    nb_neighbors: int = 20,
    std_ratio: float = 2.0,
    apply_radius_filter: bool = False,
    radius_nb_points: int = 8,
    radius: float | None = None,
) -> np.ndarray:
    """Statistical outlier removal (ARCHITECTURE.md), with radius filtering available
    but off by default. Returns the kept mask (apply it to points_xyz and every
    parallel array — colors, confidence, class tags — yourself, so this stays a pure
    filtering decision, not a data-reshaping one).

    Confirmed by direct experiment on a real COLMAP sparse reconstruction: statistical
    removal alone correctly identified and removed 3 genuinely wild outlier points out
    of 23,013 (99th percentile of coordinates was within +-4.7, but the raw max was 62 —
    a handful of weakly-triangulated points), which alone fixed a ~10x-inflated
    bounding box. Radius filtering with a naive "2x median nearest-neighbor distance"
    auto-radius, tried first, was NOT safe as an always-on default: real SfM point
    clouds have highly non-uniform density (dense clusters at well-observed surfaces,
    sparse elsewhere), and that auto-radius rejected 98.9% of points — legitimate sparse
    regions look identical to true isolated outliers under a single global radius
    threshold tuned from the (locally dense) median. Left available for callers who
    have a scene-appropriate radius in mind, but not applied unless asked for.
    """
    mask = np.zeros(points_xyz.shape[0], dtype=bool)
    stat_mask, _ = remove_statistical_outliers(points_xyz, nb_neighbors, std_ratio)
    mask[stat_mask] = True

    if apply_radius_filter:
        if radius is None:
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points_xyz[mask])
            distances = pcd.compute_nearest_neighbor_distance()
            radius = 2.0 * float(np.median(distances)) if len(distances) else 1.0

        subset_indices = np.where(mask)[0]
        radius_mask_on_subset, _ = remove_radius_outliers(points_xyz[mask], radius_nb_points, radius)
        mask = np.zeros(points_xyz.shape[0], dtype=bool)
        mask[subset_indices[radius_mask_on_subset]] = True

    return mask
