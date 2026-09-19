"""
Phase 5 — Depth + Sparse Point Fusion -> Dense Point Cloud.

Depth Anything V2 gives *relative* per-pixel depth (unscaled). We recover a per-frame
metric scale+shift by least-squares fitting the relative depth against COLMAP's own
sparse 3D points that are visible in that frame (2D-3D correspondences from the sparse
model) — a standard sparse-to-dense depth alignment approach. The resulting dense,
metrically-consistent-with-COLMAP point cloud is in the same (still GPS-unscaled) SfM
coordinate frame as the sparse cloud, so Phase 3's alignment applies identically to it.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from depth_fusion.depth_anything import DepthEstimator  # noqa: E402
from reconstruction.colmap_backend import _quat_to_rotmat, read_sparse_text_model  # noqa: E402


@dataclass
class FusedFrameResult:
    frame_name: str
    n_sparse_correspondences: int
    scale_a: float
    shift_b: float
    fit_residual: float


def _fit_scale_shift(relative_depth_at_points: np.ndarray, metric_depth_at_points: np.ndarray) -> tuple[float, float]:
    """Least-squares fit: metric_depth ~= a * relative_depth + b."""
    a_matrix = np.stack([relative_depth_at_points, np.ones_like(relative_depth_at_points)], axis=1)
    solution, residuals, _, _ = np.linalg.lstsq(a_matrix, metric_depth_at_points, rcond=None)
    return float(solution[0]), float(solution[1])


def fuse_frame(
    image_bgr: np.ndarray,
    relative_depth: np.ndarray,
    camera_rotation: np.ndarray,
    camera_translation: np.ndarray,
    camera_intrinsics: np.ndarray,
    points2d: list[tuple[float, float, int]],
    point3d_id_to_xyz: dict[int, np.ndarray],
    max_dense_points: int = 20000,
    min_correspondences: int = 8,
) -> tuple[np.ndarray, np.ndarray, FusedFrameResult] | None:
    """Returns (dense_points_xyz, dense_points_rgb, fit_result) in world coordinates,
    or None if too few sparse correspondences to fit a reliable scale+shift."""
    h, w = relative_depth.shape

    rel_depths_at_sparse = []
    metric_depths_at_sparse = []
    for u, v, point3d_id in points2d:
        xyz = point3d_id_to_xyz.get(point3d_id)
        if xyz is None:
            continue
        cam_point = camera_rotation @ xyz + camera_translation  # world -> camera
        z_cam = cam_point[2]
        if z_cam <= 0:
            continue  # behind camera, shouldn't happen for a valid correspondence
        ui, vi = int(round(u)), int(round(v))
        if not (0 <= ui < w and 0 <= vi < h):
            continue
        rel_depths_at_sparse.append(relative_depth[vi, ui])
        metric_depths_at_sparse.append(z_cam)

    n_corr = len(rel_depths_at_sparse)
    if n_corr < min_correspondences:
        return None

    rel_arr = np.array(rel_depths_at_sparse)
    metric_arr = np.array(metric_depths_at_sparse)
    a, b = _fit_scale_shift(rel_arr, metric_arr)

    fitted = a * rel_arr + b
    residual = float(np.sqrt(np.mean((fitted - metric_arr) ** 2)))

    metric_depth_map = a * relative_depth + b
    valid = metric_depth_map > 0

    ys, xs = np.where(valid)
    if len(xs) > max_dense_points:
        idx = np.random.default_rng(0).choice(len(xs), max_dense_points, replace=False)
        ys, xs = ys[idx], xs[idx]

    k_inv = np.linalg.inv(camera_intrinsics)
    pixels_hom = np.stack([xs, ys, np.ones_like(xs)], axis=1).astype(np.float64)
    rays_cam = (k_inv @ pixels_hom.T).T
    depths = metric_depth_map[ys, xs][:, None]
    points_cam = rays_cam * depths

    r_inv = camera_rotation.T
    points_world = (r_inv @ (points_cam - camera_translation).T).T

    rgb_bgr = image_bgr[ys, xs]
    points_rgb = rgb_bgr[:, ::-1]  # BGR -> RGB

    result = FusedFrameResult(
        frame_name="", n_sparse_correspondences=n_corr, scale_a=a, shift_b=b, fit_residual=residual
    )
    return points_world, points_rgb, result


def fuse_depth_for_sequence(
    image_dir: str | Path, sparse_txt_dir: str | Path, max_dense_points_per_frame: int = 20000
) -> tuple[np.ndarray, np.ndarray, list[FusedFrameResult]]:
    """Runs Depth Anything V2 + fusion over every registered frame in the sparse model.
    Returns (all_points_xyz, all_points_rgb, per_frame_fit_results)."""
    model = read_sparse_text_model(sparse_txt_dir)
    estimator = DepthEstimator()

    all_points = []
    all_rgb = []
    fit_results = []

    for image_id, img_data in model["images"].items():
        frame_path = Path(image_dir) / img_data["name"]
        image_bgr = cv2.imread(str(frame_path))
        if image_bgr is None:
            continue

        relative_depth = estimator.predict_relative_depth(image_bgr)

        r = _quat_to_rotmat(*img_data["quat_wxyz"])
        t = np.array(img_data["translation"])
        camera = model["cameras"][img_data["camera_id"]]
        from reconstruction.colmap_backend import _camera_intrinsics

        k = _camera_intrinsics(camera)

        fused = fuse_frame(
            image_bgr, relative_depth, r, t, k,
            img_data["points2d"], model["point3d_id_to_xyz"],
            max_dense_points=max_dense_points_per_frame,
        )
        if fused is None:
            continue
        points_world, points_rgb, result = fused
        result.frame_name = img_data["name"]
        all_points.append(points_world)
        all_rgb.append(points_rgb)
        fit_results.append(result)

    if not all_points:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.uint8), fit_results

    return np.concatenate(all_points), np.concatenate(all_rgb), fit_results
