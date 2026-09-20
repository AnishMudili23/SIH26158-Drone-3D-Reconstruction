"""
Phase 7 — DSM/DTM Export: grid the georeferenced point cloud into elevation rasters
(GeoTIFF), per ARCHITECTURE.md's DSM/DTM Export component.

DSM (Digital Surface Model): highest point per cell — the visible surface including
buildings/vegetation.
DTM (Digital Terrain Model): bare-earth elevation. We approximate this using only
points tagged as ground-like classes (Road, Background clutter — UAVid has no separate
"bare terrain" class; Building/Tree/vegetation points are excluded since they're
above-ground features by definition) and take the minimum Z in each cell among those.
Cells with no ground-like observation are left NaN (honestly "unknown," not
interpolated/guessed) — consistent with CLAUDE.md constraint #5.

CRS note: for a single flight's local extent (typically a few hundred meters), we treat
the Phase 3 ENU frame's (east, north) as locally equivalent to the UTM zone containing
the flight origin — the divergence between true ENU and UTM over this scale is
sub-centimeter, far below the point cloud's own accuracy. This is a documented
approximation, not an exact reprojection.
"""
from __future__ import annotations

import numpy as np
import rasterio
from rasterio.transform import from_origin


def utm_epsg_for_lonlat(lon: float, lat: float) -> int:
    zone = int((lon + 180) / 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def grid_elevation(
    points_enu: np.ndarray,
    values: np.ndarray | None,
    cell_size_m: float,
    agg: str,
    bounds: tuple[float, float, float, float] | None = None,
) -> tuple[np.ndarray, float, float]:
    """Grids (x, y) -> aggregated Z (or `values` if given) at `cell_size_m` resolution.
    agg: 'max' (DSM) or 'min' (DTM). Returns (grid (rows, cols), x_min, y_max) — y_max
    because raster row 0 is the northernmost row (standard GeoTIFF row-major-from-top
    convention)."""
    x, y, z = points_enu[:, 0], points_enu[:, 1], values if values is not None else points_enu[:, 2]
    if bounds is not None:
        x_min, x_max, y_min, y_max = bounds
    else:
        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()

    n_cols = max(1, int(np.ceil((x_max - x_min) / cell_size_m)))
    n_rows = max(1, int(np.ceil((y_max - y_min) / cell_size_m)))

    col_idx = np.clip(((x - x_min) / cell_size_m).astype(int), 0, n_cols - 1)
    # Row 0 = north edge, so flip the row index (y increases north but row increases south).
    row_idx = np.clip((n_rows - 1) - ((y - y_min) / cell_size_m).astype(int), 0, n_rows - 1)

    # np.maximum.at/np.minimum.at propagate NaN forever if the accumulator starts as
    # NaN (max(nan, x) is nan under IEEE semantics) — start from +-inf instead and
    # convert untouched (still-infinite) cells to NaN afterwards.
    if agg == "max":
        grid_filled = np.full((n_rows, n_cols), -np.inf, dtype=np.float32)
        np.maximum.at(grid_filled, (row_idx, col_idx), z)
    elif agg == "min":
        grid_filled = np.full((n_rows, n_cols), np.inf, dtype=np.float32)
        np.minimum.at(grid_filled, (row_idx, col_idx), z)
    else:
        raise ValueError(f"Unknown agg: {agg}")
    grid = np.where(np.isfinite(grid_filled), grid_filled, np.nan)

    return grid, float(x_min), float(y_max)


def write_geotiff(
    grid: np.ndarray, x_min: float, y_max: float, cell_size_m: float, epsg: int, out_path: str
) -> None:
    transform = from_origin(x_min, y_max, cell_size_m, cell_size_m)
    with rasterio.open(
        out_path, "w", driver="GTiff", height=grid.shape[0], width=grid.shape[1],
        count=1, dtype=grid.dtype, crs=f"EPSG:{epsg}", transform=transform, nodata=np.nan,
    ) as dst:
        dst.write(grid, 1)


def compute_volumetric_metrics(
    dsm_grid: np.ndarray,
    dtm_grid: np.ndarray,
    cell_size_m: float,
    min_height_m: float = 0.5,
) -> dict[str, float]:
    """Computes volumetric and relief metrics from DSM and DTM elevation models.

    Calculates:
      - total_above_ground_volume_m3: integral of (DSM - DTM) for cells where DSM > DTM + min_height_m
      - elevated_surface_area_m2: ground footprint of elevated features
      - mean_elevated_height_m: average height above ground of elevated features
      - max_height_m: peak height above ground
    """
    valid_mask = np.isfinite(dsm_grid) & np.isfinite(dtm_grid)
    if not np.any(valid_mask):
        return {
            "total_above_ground_volume_m3": 0.0,
            "elevated_surface_area_m2": 0.0,
            "mean_elevated_height_m": 0.0,
            "max_height_m": 0.0,
        }

    diff = dsm_grid[valid_mask] - dtm_grid[valid_mask]
    elevated = diff > min_height_m
    cell_area = cell_size_m ** 2

    if np.any(elevated):
        vol = float(np.sum(diff[elevated]) * cell_area)
        area = float(np.sum(elevated) * cell_area)
        mean_h = float(np.mean(diff[elevated]))
        max_h = float(np.max(diff[elevated]))
    else:
        vol = 0.0
        area = 0.0
        mean_h = 0.0
        max_h = 0.0

    return {
        "total_above_ground_volume_m3": vol,
        "elevated_surface_area_m2": area,
        "mean_elevated_height_m": mean_h,
        "max_height_m": max_h,
    }


def export_dsm_dtm(
    points_enu: np.ndarray,
    class_names: list[str],
    origin_lat: float,
    origin_lon: float,
    dsm_out_path: str,
    dtm_out_path: str,
    cell_size_m: float = 1.0,
    ground_like_classes: tuple[str, ...] = ("Road", "Background clutter"),
) -> dict:
    epsg = utm_epsg_for_lonlat(origin_lon, origin_lat)

    x_min, y_min = points_enu[:, :2].min(axis=0)
    x_max, y_max = points_enu[:, :2].max(axis=0)
    shared_bounds = (float(x_min), float(x_max), float(y_min), float(y_max))

    dsm_grid, _, _ = grid_elevation(points_enu, None, cell_size_m, agg="max", bounds=shared_bounds)
    write_geotiff(dsm_grid, float(x_min), float(y_max), cell_size_m, epsg, dsm_out_path)

    ground_mask = np.array([c in ground_like_classes for c in class_names])
    n_ground_points = int(ground_mask.sum())
    if n_ground_points > 0:
        dtm_grid, _, _ = grid_elevation(
            points_enu[ground_mask], None, cell_size_m, agg="min", bounds=shared_bounds
        )
    else:
        dtm_grid = np.full_like(dsm_grid, np.nan)
    write_geotiff(dtm_grid, float(x_min), float(y_max), cell_size_m, epsg, dtm_out_path)

    volumetric_stats = compute_volumetric_metrics(dsm_grid, dtm_grid, cell_size_m)

    return {
        "epsg": epsg,
        "cell_size_m": cell_size_m,
        "dsm_shape": dsm_grid.shape,
        "dtm_shape": dtm_grid.shape,
        "n_ground_points_for_dtm": n_ground_points,
        "pct_dtm_cells_unknown": float(np.isnan(dtm_grid).mean() * 100),
        "volumetric": volumetric_stats,
    }
