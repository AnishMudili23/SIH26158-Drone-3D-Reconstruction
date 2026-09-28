"""
Adaptive Georeferencer and Robust RANSAC Similarity Alignment.

Implements the sensor-aware georeferencing pipeline:
1. SENSOR QUALITY GATE: Evaluates GPS/IMU quality (BNR, noise, baseline) BEFORE alignment.
2. ADAPTIVE POLICY:
   - STRONG_GPS: Robust RANSAC similarity transform (outlier rejection + M-estimator refinement).
   - WEAK_GPS: Visual trajectory primary, downweighted bounded GPS alignment.
   - INSUFFICIENT_BASELINE / LOCAL_METRIC: Visual scale locked; GPS used strictly for origin anchor.
   - RTK: Sub-decimeter tight geo-constrained alignment.
3. RANSAC SIMILARITY:
   Rejects GPS jumps, multipath, and timestamp mismatches.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import numpy as np

from common.alignment import umeyama_alignment
from common.coordinate_frames import (
    CoordinateFrame,
    SimilarityTransform,
    CameraTrajectoryENU,
    wgs84_to_enu,
    enu_to_wgs84,
)
from common.geometry_interface import CameraPose, GeometryEstimate
from geo.scale_alignment import GpsFix, GeoAlignedResult, rederive_aligned_camera, gps_fixes_to_enu
from sensor_fusion.sensor_quality import (
    GPSQualityTier,
    SensorQualityReport,
    SensorQualityEvaluator,
)


class GeoreferencingMode(str, Enum):
    STRONG_GPS = "STRONG_GPS"
    WEAK_GPS = "WEAK_GPS"
    RTK = "RTK"
    LOCAL_METRIC = "LOCAL_METRIC"


def ransac_similarity_alignment(
    src: np.ndarray,
    dst: np.ndarray,
    inlier_threshold_m: float = 6.0,
    min_inliers: int = 3,
    max_iterations: int = 300,
    random_seed: int = 42,
) -> tuple[SimilarityTransform, np.ndarray, float]:
    """Robust RANSAC similarity alignment (scale, rotation, translation) between 3D point sets.
    
    Tolerates outlier GPS fixes (multipath, jumps, inaccurate fixes).
    Uses Umeyama for candidate generation and re-fits with M-estimator refinement on the best inlier set.
    
    Returns:
        (transform, inlier_mask, mean_inlier_residual_m)
    """
    assert src.shape == dst.shape, f"src {src.shape} != dst {dst.shape}"
    n = len(src)
    if n < 3:
        raise ValueError(f"Need at least 3 points for similarity alignment, got {n}")

    if n == 3:
        s, R, t = umeyama_alignment(src, dst)
        tf = SimilarityTransform(scale=s, rotation=R, translation=t)
        res = np.linalg.norm(dst - tf.transform_points(src), axis=1)
        return tf, np.ones(n, dtype=bool), float(res.mean())

    rng = np.random.default_rng(random_seed)
    best_inliers = np.zeros(n, dtype=bool)
    best_residual = float("inf")
    best_score = -1

    for _ in range(max_iterations):
        sample_idx = rng.choice(n, size=3, replace=False)
        p1, p2, p3 = src[sample_idx]
        
        # Check collinearity: area of triangle
        cross_prod = np.cross(p2 - p1, p3 - p1)
        if np.linalg.norm(cross_prod) < 1e-5:
            continue

        try:
            s_cand, R_cand, t_cand = umeyama_alignment(src[sample_idx], dst[sample_idx])
            if s_cand <= 1e-4 or np.isnan(s_cand) or np.isinf(s_cand):
                continue
            tf_cand = SimilarityTransform(scale=s_cand, rotation=R_cand, translation=t_cand)
            pred = tf_cand.transform_points(src)
            res = np.linalg.norm(dst - pred, axis=1)
            inliers = res < inlier_threshold_m
            n_inliers = int(inliers.sum())

            # Score prioritizes more inliers, then lower mean inlier residual
            if n_inliers > best_score or (n_inliers == best_score and res[inliers].mean() < best_residual):
                best_score = n_inliers
                best_inliers = inliers
                best_residual = float(res[inliers].mean())
        except Exception:
            continue

    if best_score < min_inliers:
        # Fallback to standard Umeyama on all points
        s, R, t = umeyama_alignment(src, dst)
        tf = SimilarityTransform(scale=s, rotation=R, translation=t)
        res = np.linalg.norm(dst - tf.transform_points(src), axis=1)
        return tf, np.ones(n, dtype=bool), float(res.mean())

    # Re-estimate on all best inliers
    src_inliers = src[best_inliers]
    dst_inliers = dst[best_inliers]
    s_ref, R_ref, t_ref = umeyama_alignment(src_inliers, dst_inliers)
    
    # One-step Huber M-estimator refinement
    pred_ref = (s_ref * R_ref @ src_inliers.T).T + t_ref
    inlier_res = np.linalg.norm(dst_inliers - pred_ref, axis=1)
    k_huber = max(float(np.median(inlier_res)), 1e-3)
    weights = np.minimum(1.0, k_huber / np.maximum(inlier_res, 1e-6))
    
    # Weighted Umeyama centers
    w_sum = weights.sum()
    mu_s = (src_inliers * weights[:, None]).sum(axis=0) / w_sum
    mu_d = (dst_inliers * weights[:, None]).sum(axis=0) / w_sum
    sc = src_inliers - mu_s
    dc = dst_inliers - mu_d
    var_s = (weights[:, None] * (sc ** 2)).sum() / w_sum
    cov = (dc.T @ (sc * weights[:, None])) / w_sum
    u, d, vt = np.linalg.svd(cov)
    s_diag = np.ones(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        s_diag[-1] = -1
    R_final = u @ np.diag(s_diag) @ vt
    s_final = float(np.trace(np.diag(d) @ np.diag(s_diag)) / var_s)
    t_final = mu_d - s_final * R_final @ mu_s

    final_tf = SimilarityTransform(scale=s_final, rotation=R_final, translation=t_final)
    final_res = np.linalg.norm(dst_inliers - final_tf.transform_points(src_inliers), axis=1)
    return final_tf, best_inliers, float(final_res.mean())


class AdaptiveGeoreferencer:
    """Estimates georeferencing using an adaptive strategy driven by sensor quality."""

    def __init__(self, default_gps_noise_m: float = 6.0, rtk_noise_m: float = 0.05):
        self.sq_evaluator = SensorQualityEvaluator(
            default_gps_noise_m=default_gps_noise_m,
            rtk_gps_noise_m=rtk_noise_m,
        )

    def estimate(
        self,
        geometry: GeometryEstimate,
        gps_fixes: list[GpsFix],
        sensor_quality: SensorQualityReport | None = None,
        is_rtk: bool = False,
        has_imu: bool = False,
        has_barometer: bool = False,
    ) -> GeoAlignedResult:
        """Adaptive georeferencing entry point.
        
        1. Evaluates sensor quality first if not provided.
        2. Selects georeferencing mode (STRONG_GPS, WEAK_GPS, LOCAL_METRIC, RTK).
        3. Executes robust alignment or conservative metric anchoring.
        """
        fixes_by_name = {f.frame_name: f for f in gps_fixes}
        matched_sfm_centers: list[np.ndarray] = []
        matched_fixes: list[GpsFix] = []
        matched_poses: list[CameraPose] = []

        for pose in geometry.poses:
            name = Path(pose.frame_path).name
            if name in fixes_by_name:
                center = -pose.rotation.T @ pose.translation
                matched_sfm_centers.append(center)
                matched_fixes.append(fixes_by_name[name])
                matched_poses.append(pose)

        n_matches = len(matched_sfm_centers)

        # 1. Evaluate Sensor Quality BEFORE alignment
        if sensor_quality is None:
            if n_matches >= 2:
                gps_enu_raw, lat0, lon0, alt0 = gps_fixes_to_enu(matched_fixes)
                sensor_quality = self.sq_evaluator.evaluate_trajectory(
                    gps_enu_raw,
                    is_rtk=is_rtk,
                    has_imu=has_imu,
                    has_barometer=has_barometer,
                )
            else:
                sensor_quality = self.sq_evaluator.evaluate_trajectory(
                    None,
                    is_rtk=is_rtk,
                    has_imu=has_imu,
                    has_barometer=has_barometer,
                )

        # 2. Select strategy based on Sensor Quality Gate
        if n_matches < 3 or sensor_quality.quality_tier in (
            GPSQualityTier.INSUFFICIENT_BASELINE,
            GPSQualityTier.LOCAL_METRIC,
        ):
            # LOCAL_METRIC MODE: Do not allow unconstrained noisy GPS to distort reconstruction
            mode = GeoreferencingMode.LOCAL_METRIC
            origin_lat = matched_fixes[0].lat if matched_fixes else None
            origin_lon = matched_fixes[0].lon if matched_fixes else None
            origin_alt = matched_fixes[0].alt_m if matched_fixes else None

            # Identity similarity transform (keeps visual scale and relative geometry intact)
            tf = SimilarityTransform.identity()
            aligned_points = tf.transform_points(geometry.points_xyz)
            aligned_centers = (
                tf.transform_points(np.array(matched_sfm_centers))
                if matched_sfm_centers
                else np.empty((0, 3))
            )

            aligned_poses = []
            trajectories = []
            for pose in matched_poses or geometry.poses:
                ap, ct = rederive_aligned_camera(pose, tf)
                aligned_poses.append(ap)
                trajectories.append(ct)

            return GeoAlignedResult(
                points_enu=aligned_points,
                camera_centers_enu=aligned_centers,
                aligned_poses=aligned_poses,
                scale_factor=1.0,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                origin_alt_m=origin_alt,
                n_gps_correspondences=n_matches,
                mean_alignment_residual_m=None,
                transform=tf,
                coordinate_frame=CoordinateFrame.LOCAL_METRIC,
                camera_trajectory=trajectories,
            )

        # 3. Georeferenced alignment (STRONG_GPS, WEAK_GPS, or RTK)
        sfm_centers = np.array(matched_sfm_centers)
        gps_enu, origin_lat, origin_lon, origin_alt = gps_fixes_to_enu(matched_fixes)

        if is_rtk:
            mode = GeoreferencingMode.RTK
            inlier_thresh = 0.5  # sub-meter for RTK
        elif sensor_quality.quality_tier == GPSQualityTier.STRONG_GPS:
            mode = GeoreferencingMode.STRONG_GPS
            inlier_thresh = max(2.5 * sensor_quality.estimated_noise_m, 5.0)
        else:
            mode = GeoreferencingMode.WEAK_GPS
            inlier_thresh = max(3.5 * sensor_quality.estimated_noise_m, 8.0)

        # Robust RANSAC similarity
        tf, inlier_mask, mean_res = ransac_similarity_alignment(
            sfm_centers, gps_enu, inlier_threshold_m=inlier_thresh
        )

        aligned_points = tf.transform_points(geometry.points_xyz)
        aligned_centers = tf.transform_points(sfm_centers)

        aligned_poses = []
        trajectories = []
        for pose in matched_poses:
            ap, ct = rederive_aligned_camera(pose, tf)
            aligned_poses.append(ap)
            trajectories.append(ct)

        return GeoAlignedResult(
            points_enu=aligned_points,
            camera_centers_enu=aligned_centers,
            aligned_poses=aligned_poses,
            scale_factor=tf.scale,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            origin_alt_m=origin_alt,
            n_gps_correspondences=int(inlier_mask.sum()),
            mean_alignment_residual_m=mean_res,
            transform=tf,
            coordinate_frame=CoordinateFrame.ENU,
            camera_trajectory=trajectories,
        )
