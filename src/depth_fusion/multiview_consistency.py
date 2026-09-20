from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np


@dataclass
class ViewCamera:
    rotation: np.ndarray    # (3, 3) world-to-cam
    translation: np.ndarray # (3,) world-to-cam
    intrinsics: np.ndarray  # (3, 3) K matrix
    width: int
    height: int


class MultiViewDepthConsistencyFilter:
    """Evaluates multi-view geometric consistency of monocular/AI depth predictions by
    cross-reprojecting 3D points into neighboring camera views and checking photometric/geometric agreement."""

    def __init__(
        self,
        max_relative_depth_error: float = 0.05,  # 5% relative depth error tolerance
        min_consistent_views: int = 1,           # must agree with at least 1 neighboring view
        error_sigma: float = 0.03,
    ):
        self.max_rel_error = max_relative_depth_error
        self.min_consistent_views = min_consistent_views
        self.error_sigma = error_sigma

    def check_consistency_pair(
        self,
        depth_a: np.ndarray,
        cam_a: ViewCamera,
        depth_b: np.ndarray,
        cam_b: ViewCamera,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Reprojects depth_a into camera_b and checks depth agreement.
        
        Returns:
            is_consistent: boolean mask of shape (H, W)
            relative_error: float array of shape (H, W) with relative depth discrepancies
        """
        h, w = depth_a.shape
        y_coords, x_coords = np.indices((h, w), dtype=np.float32)

        # Unproject pixel rays in camera A frame
        k_inv_a = np.linalg.inv(cam_a.intrinsics)
        pixels_homo = np.stack([x_coords, y_coords, np.ones_like(x_coords)], axis=-1)  # (H, W, 3)
        rays_a = (k_inv_a @ pixels_homo.reshape(-1, 3).T).T.reshape(h, w, 3)
        pts_cam_a = rays_a * depth_a[..., np.newaxis]

        # Transform to world frame: X = R_a^T (X_cam_a - t_a)
        r_a_t = cam_a.rotation.T
        pts_world = (r_a_t @ (pts_cam_a.reshape(-1, 3) - cam_a.translation).T).T

        # Transform to camera B frame: X_cam_b = R_b X_world + t_b
        pts_cam_b = (cam_b.rotation @ pts_world.T + cam_b.translation[:, np.newaxis]).T
        pts_cam_b = pts_cam_b.reshape(h, w, 3)

        depth_proj_b = pts_cam_b[..., 2]

        # Project onto camera B sensor plane
        fx_b, fy_b = cam_b.intrinsics[0, 0], cam_b.intrinsics[1, 1]
        cx_b, cy_b = cam_b.intrinsics[0, 2], cam_b.intrinsics[1, 2]

        # Avoid division by zero
        valid_z = depth_proj_b > 1e-3
        safe_z = np.where(valid_z, depth_proj_b, 1.0)
        u_b = (fx_b * pts_cam_b[..., 0] / safe_z) + cx_b
        v_b = (fy_b * pts_cam_b[..., 1] / safe_z) + cy_b

        # Bounds check in camera B image plane
        in_bounds = valid_z & (u_b >= 0) & (u_b < cam_b.width - 1) & (v_b >= 0) & (v_b < cam_b.height - 1)

        # Sample depth in camera B using bilinear interpolation
        u_clamped = np.clip(u_b, 0, cam_b.width - 1).astype(np.float32)
        v_clamped = np.clip(v_b, 0, cam_b.height - 1).astype(np.float32)
        sampled_depth_b = cv2.remap(
            depth_b.astype(np.float32),
            u_clamped,
            v_clamped,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

        valid_sample = in_bounds & (sampled_depth_b > 1e-3)
        safe_sampled_b = np.where(valid_sample, sampled_depth_b, 1.0)

        rel_error = np.where(
            valid_sample,
            np.abs(depth_proj_b - sampled_depth_b) / safe_sampled_b,
            1.0,
        )

        is_consistent = valid_sample & (rel_error <= self.max_rel_error)
        return is_consistent, rel_error

    def compute_view_confidence(
        self,
        ref_depth: np.ndarray,
        ref_cam: ViewCamera,
        neighbor_depths: Sequence[np.ndarray],
        neighbor_cams: Sequence[ViewCamera],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Evaluates reference depth against multiple neighboring views.
        
        Returns:
            consistent_mask: boolean mask (H, W) where consensus >= min_consistent_views
            confidence_weights: float array (H, W) in [0.0, 1.0] representing geometric certainty
        """
        h, w = ref_depth.shape
        consensus_count = np.zeros((h, w), dtype=np.int32)
        accumulated_score = np.zeros((h, w), dtype=np.float32)

        for n_depth, n_cam in zip(neighbor_depths, neighbor_cams):
            consistent, rel_err = self.check_consistency_pair(ref_depth, ref_cam, n_depth, n_cam)
            consensus_count += consistent.astype(np.int32)
            score = np.exp(-(rel_err**2) / (2.0 * (self.error_sigma**2)))
            accumulated_score += np.where(consistent, score, 0.0)

        consistent_mask = consensus_count >= self.min_consistent_views
        num_neighbors = max(len(neighbor_depths), 1)
        confidence_weights = np.clip(accumulated_score / num_neighbors, 0.0, 1.0)

        return consistent_mask, confidence_weights

    @staticmethod
    def fuse_mvs_and_ai_depth(
        mvs_depth: np.ndarray | None,
        mvs_confidence: np.ndarray | None,
        ai_depth: np.ndarray,
        ai_consistency_weight: np.ndarray,
    ) -> np.ndarray:
        """Blends classical MVS depth and AI depth prior:
        - High MVS confidence: MVS dominates.
        - Weak/missing MVS + high AI consistency: AI fills the gap.
        - Inconsistent AI depth (ai_consistency_weight near 0): AI is rejected.
        """
        if mvs_depth is None or mvs_confidence is None:
            # Fall back to AI depth masked by consistency
            return np.where(ai_consistency_weight > 0.3, ai_depth, np.nan)

        w_mvs = np.clip(mvs_confidence, 0.0, 1.0)
        w_ai = np.clip(ai_consistency_weight * (1.0 - w_mvs), 0.0, 1.0)
        total_w = w_mvs + w_ai

        valid = total_w > 1e-4
        fused = np.where(
            valid,
            (w_mvs * mvs_depth + w_ai * ai_depth) / np.where(valid, total_w, 1.0),
            np.nan,
        )
        return fused
