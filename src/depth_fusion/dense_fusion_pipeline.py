"""
Dense AI Depth Fusion Pipeline with Multi-View Consistency Gating.

Flow:
COLMAP sparse geometry
      │
      ├───────────────────────┐
      ▼                       ▼
   MVS sparse depth        Depth Anything V2
      │                       │
      │                       ▼
      │               AI relative depth
      │                       │
      └───────────┬───────────┘
                  ▼
          Scale / shift fitting
                  │
                  ▼
       Multi-view consistency check
                  │
          ┌───────┴───────┐
          ▼               ▼
      consistent       rejected
          │               │
          └───────┬───────┘
                  ▼
          Confidence-weighted fusion
                  │
                  ▼
             Dense cloud (XYZ + RGB + Confidence + Source)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from depth_fusion.depth_anything import DepthEstimator
from depth_fusion.multiview_consistency import MultiViewDepthConsistencyFilter, ViewCamera


class DepthSource(str, Enum):
    MVS = "MVS"
    AI = "AI"
    MVS_AI = "AI+MVS"
    UNOBSERVED = "UNOBSERVED"
    REJECTED = "REJECTED"


@dataclass
class DensePointBatch:
    points_xyz: np.ndarray       # (N, 3) metric world points
    points_rgb: np.ndarray       # (N, 3) uint8 colors
    confidences: np.ndarray      # (N,) float [0, 1]
    sources: list[str]           # (N,) source strings
    n_consistent: int
    n_rejected: int


class DenseDepthFusionPipeline:
    """Orchestrates Depth Anything V2 monocular estimation, sparse-to-metric scale/shift
    fitting, and multi-view geometric consistency verification."""

    def __init__(
        self,
        max_rel_depth_err: float = 0.05,
        min_consistent_views: int = 1,
        max_points_per_view: int = 15000,
        device: str | None = None,
    ):
        self.estimator = DepthEstimator(device=device)
        self.consistency_filter = MultiViewDepthConsistencyFilter(
            max_relative_depth_error=max_rel_depth_err,
            min_consistent_views=min_consistent_views,
        )
        self.max_points_per_view = max_points_per_view

    def fit_metric_depth(
        self,
        relative_depth: np.ndarray,
        camera_rotation: np.ndarray,
        camera_translation: np.ndarray,
        points2d: list[tuple[float, float, int]],
        point3d_id_to_xyz: dict[int, np.ndarray],
        min_correspondences: int = 6,
    ) -> tuple[np.ndarray | None, float, float, float]:
        """Fits metric depth map z_metric = a * z_rel + b against visible sparse 3D points.
        
        Returns:
            (metric_depth_map, scale_a, shift_b, residual_m)
        """
        h, w = relative_depth.shape[:2]
        rel_vals, metric_vals = [], []

        for u, v, pid in points2d:
            xyz = point3d_id_to_xyz.get(pid)
            if xyz is None:
                continue
            p_cam = camera_rotation @ xyz + camera_translation
            z = p_cam[2]
            if z <= 0.1:
                continue
            ui, vi = int(round(u)), int(round(v))
            if 0 <= ui < w and 0 <= vi < h:
                rel_vals.append(relative_depth[vi, ui])
                metric_vals.append(z)

        if len(rel_vals) < min_correspondences:
            return None, 1.0, 0.0, 999.0

        rel_arr = np.array(rel_vals, dtype=np.float64)
        metric_arr = np.array(metric_vals, dtype=np.float64)

        # Robust Theil-Sen or Least Squares fit
        a_mat = np.stack([rel_arr, np.ones_like(rel_arr)], axis=1)
        sol, residuals, _, _ = np.linalg.lstsq(a_mat, metric_arr, rcond=None)
        scale_a, shift_b = float(sol[0]), float(sol[1])

        fitted = scale_a * rel_arr + shift_b
        res = float(np.sqrt(np.mean((fitted - metric_arr) ** 2)))

        metric_depth = scale_a * relative_depth + shift_b
        metric_depth = np.where(metric_depth > 0.1, metric_depth, np.nan)
        return metric_depth, scale_a, shift_b, res

    def process_frame(
        self,
        image_bgr: np.ndarray,
        camera_rotation: np.ndarray,
        camera_translation: np.ndarray,
        camera_intrinsics: np.ndarray,
        points2d: list[tuple[float, float, int]],
        point3d_id_to_xyz: dict[int, np.ndarray],
        neighbor_depths: Sequence[np.ndarray] = (),
        neighbor_cams: Sequence[ViewCamera] = (),
        dynamic_mask: np.ndarray | None = None,
    ) -> DensePointBatch | None:
        """Processes a single frame: predicts AI depth, fits metric scale, evaluates
        multi-view consistency, and unprojects verified pixels to dense 3D points.
        """
        h, w = image_bgr.shape[:2]
        rel_depth = self.estimator.predict_relative_depth(image_bgr)

        metric_depth, a, b, fit_res = self.fit_metric_depth(
            rel_depth, camera_rotation, camera_translation, points2d, point3d_id_to_xyz
        )
        if metric_depth is None:
            return None

        ref_cam = ViewCamera(
            rotation=camera_rotation,
            translation=camera_translation,
            intrinsics=camera_intrinsics,
            width=w,
            height=h,
        )

        # Multi-view consistency check
        if neighbor_depths and neighbor_cams:
            consistent_mask, confidence_weights = self.consistency_filter.compute_view_confidence(
                metric_depth, ref_cam, neighbor_depths, neighbor_cams
            )
        else:
            # Baseline single-view confidence derived from scale/shift fit residual
            fit_conf = float(np.clip(1.0 / (1.0 + fit_res), 0.3, 0.95))
            consistent_mask = ~np.isnan(metric_depth)
            confidence_weights = np.full((h, w), fit_conf, dtype=np.float32)

        # Exclude dynamic object pixels from dense geometry
        if dynamic_mask is not None:
            consistent_mask &= ~dynamic_mask

        # Unproject consistent pixels to metric world coordinates
        valid_ys, valid_xs = np.where(consistent_mask & ~np.isnan(metric_depth))
        n_total_valid = len(valid_xs)
        if n_total_valid == 0:
            return None

        # Downsample if exceeding max_points_per_view
        if n_total_valid > self.max_points_per_view:
            idx = np.random.default_rng(0).choice(n_total_valid, self.max_points_per_view, replace=False)
            valid_ys, valid_xs = valid_ys[idx], valid_xs[idx]

        depths = metric_depth[valid_ys, valid_xs]
        confs = confidence_weights[valid_ys, valid_xs]

        k_inv = np.linalg.inv(camera_intrinsics)
        pixels_homo = np.stack([valid_xs, valid_ys, np.ones_like(valid_xs)], axis=1)
        rays_cam = (k_inv @ pixels_homo.T).T
        pts_cam = rays_cam * depths[:, None]

        r_inv = camera_rotation.T
        pts_world = (r_inv @ (pts_cam - camera_translation).T).T

        rgb_bgr = image_bgr[valid_ys, valid_xs]
        pts_rgb = rgb_bgr[:, ::-1]  # BGR -> RGB

        # Identify source
        sources = [DepthSource.MVS_AI.value if c >= 0.8 else DepthSource.AI.value for c in confs]
        n_rejected = int((~consistent_mask).sum())

        return DensePointBatch(
            points_xyz=pts_world,
            points_rgb=pts_rgb,
            confidences=confs,
            sources=sources,
            n_consistent=len(pts_world),
            n_rejected=n_rejected,
        )
