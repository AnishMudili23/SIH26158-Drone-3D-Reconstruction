"""
Phase 6 — Confidence / Coverage Reporting.

Per ARCHITECTURE.md's Confidence Module: score density/reprojection error per region,
including per-class. Per PRD.md Section 5 / CLAUDE.md hard constraint #5: never present
raw model output as ground truth — every point gets an honest per-point confidence tier
derived from two independent signals COLMAP already gives us for free:

  - track length (how many frames triangulated this point — more views = more
    independently corroborated, i.e. more trustworthy)
  - reprojection error (COLMAP's own measure of how well the triangulated point actually
    projects back into its observing images — lower = more geometrically consistent)

A point is "high" confidence only if BOTH signals agree it's trustworthy; either signal
alone being bad drags the tier down. This is a deliberately conservative combination —
the failure mode we want is under-claiming confidence, never over-claiming it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Tuned as reasonable starting thresholds, not derived from a specific paper — revisit
# once run against real reconstructions (log any retuning here).
HIGH_MIN_TRACK_LEN = 5
HIGH_MAX_REPROJ_ERROR_PX = 1.0
MEDIUM_MIN_TRACK_LEN = 3
MEDIUM_MAX_REPROJ_ERROR_PX = 2.0

CONFIDENCE_TIERS = ["low", "medium", "high"]


def compute_confidence_tiers(track_len: np.ndarray, reprojection_error: np.ndarray) -> np.ndarray:
    """Returns a (N,) array of tier indices: 0=low, 1=medium, 2=high."""
    tiers = np.zeros(track_len.shape[0], dtype=np.uint8)  # default low

    is_medium = (track_len >= MEDIUM_MIN_TRACK_LEN) & (reprojection_error <= MEDIUM_MAX_REPROJ_ERROR_PX)
    tiers[is_medium] = 1

    is_high = (track_len >= HIGH_MIN_TRACK_LEN) & (reprojection_error <= HIGH_MAX_REPROJ_ERROR_PX)
    tiers[is_high] = 2

    return tiers


@dataclass
class ClassConfidenceBreakdown:
    class_name: str
    n_points: int
    pct_high: float
    pct_medium: float
    pct_low: float
    mean_track_len: float
    mean_reprojection_error_px: float


def per_class_confidence_breakdown(
    tiers: np.ndarray, track_len: np.ndarray, reprojection_error: np.ndarray, class_names: list[str]
) -> list[ClassConfidenceBreakdown]:
    results = []
    class_names_arr = np.array(class_names)
    for cls in sorted(set(class_names)):
        mask = class_names_arr == cls
        n = int(mask.sum())
        if n == 0:
            continue
        cls_tiers = tiers[mask]
        results.append(ClassConfidenceBreakdown(
            class_name=cls,
            n_points=n,
            pct_high=float((cls_tiers == 2).mean() * 100),
            pct_medium=float((cls_tiers == 1).mean() * 100),
            pct_low=float((cls_tiers == 0).mean() * 100),
            mean_track_len=float(track_len[mask].mean()),
            mean_reprojection_error_px=float(reprojection_error[mask].mean()),
        ))
    return results


@dataclass
class RegionGrid:
    """A 2D (top-down) grid over the point cloud's XY extent, cell size in meters.
    mean_confidence_tier is NaN for cells with zero points (i.e. genuinely unobserved —
    the honest "we don't know" case CLAUDE.md constraint #5 requires, distinct from
    "observed but low confidence")."""
    cell_size_m: float
    x_min: float
    y_min: float
    n_cols: int
    n_rows: int
    point_count_grid: np.ndarray       # (n_rows, n_cols) int
    mean_tier_grid: np.ndarray         # (n_rows, n_cols) float, NaN where point_count==0


def build_region_grid(points_xyz: np.ndarray, tiers: np.ndarray, cell_size_m: float = 5.0) -> RegionGrid:
    """Bins points into a top-down (X-Y) grid and reports point density + mean
    confidence tier per cell — the basis for Phase 8's confidence overlay."""
    x_min, y_min = points_xyz[:, 0].min(), points_xyz[:, 1].min()
    x_max, y_max = points_xyz[:, 0].max(), points_xyz[:, 1].max()

    n_cols = max(1, int(np.ceil((x_max - x_min) / cell_size_m)))
    n_rows = max(1, int(np.ceil((y_max - y_min) / cell_size_m)))

    col_idx = np.clip(((points_xyz[:, 0] - x_min) / cell_size_m).astype(int), 0, n_cols - 1)
    row_idx = np.clip(((points_xyz[:, 1] - y_min) / cell_size_m).astype(int), 0, n_rows - 1)

    point_count_grid = np.zeros((n_rows, n_cols), dtype=int)
    tier_sum_grid = np.zeros((n_rows, n_cols), dtype=float)

    np.add.at(point_count_grid, (row_idx, col_idx), 1)
    np.add.at(tier_sum_grid, (row_idx, col_idx), tiers.astype(float))

    with np.errstate(invalid="ignore", divide="ignore"):
        mean_tier_grid = np.where(point_count_grid > 0, tier_sum_grid / np.maximum(point_count_grid, 1), np.nan)

    return RegionGrid(
        cell_size_m=cell_size_m, x_min=float(x_min), y_min=float(y_min),
        n_cols=n_cols, n_rows=n_rows,
        point_count_grid=point_count_grid, mean_tier_grid=mean_tier_grid,
    )


@dataclass
class ConfidenceReport:
    n_points: int
    pct_high: float
    pct_medium: float
    pct_low: float
    per_class: list[ClassConfidenceBreakdown]
    region_grid: RegionGrid
    pct_grid_cells_unobserved: float  # cells with zero points, within the point cloud's own bounding box


def build_confidence_report(
    points_xyz: np.ndarray,
    track_len: np.ndarray,
    reprojection_error: np.ndarray,
    class_names: list[str],
    region_cell_size_m: float = 5.0,
) -> ConfidenceReport:
    tiers = compute_confidence_tiers(track_len, reprojection_error)
    per_class = per_class_confidence_breakdown(tiers, track_len, reprojection_error, class_names)
    region_grid = build_region_grid(points_xyz, tiers, cell_size_m=region_cell_size_m)

    n_cells = region_grid.n_rows * region_grid.n_cols
    n_unobserved = int((region_grid.point_count_grid == 0).sum())

    return ConfidenceReport(
        n_points=points_xyz.shape[0],
        pct_high=float((tiers == 2).mean() * 100),
        pct_medium=float((tiers == 1).mean() * 100),
        pct_low=float((tiers == 0).mean() * 100),
        per_class=per_class,
        region_grid=region_grid,
        pct_grid_cells_unobserved=float(n_unobserved / n_cells * 100) if n_cells else 0.0,
    )
