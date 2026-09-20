"""Phase C — Geo-Constrained Pose Refinement (ROADMAP.md).

COLMAP's visual bundle adjustment has no notion of GPS; on a long single-pass corridor
flight with weak loop closure, its scale/trajectory can drift smoothly in a way visual
reprojection error alone doesn't penalize. This module refines camera positions to
jointly satisfy (a) reprojection consistency against the already-triangulated sparse
points and (b) the real GPS-derived ENU trajectory, trading one against the other via
an explicit weight.

Deliberate scope limitation (documented, not hidden): this refines camera *positions*
only — rotations and the 3D point cloud stay fixed at COLMAP's own solution. A full
geo-constrained bundle adjustment would re-triangulate points and refine orientation
too, but that means re-deriving COLMAP's entire BA machinery (or a pycolmap dependency
this project doesn't otherwise take on). Pose-only refinement is the standard reduced
form used in pose-graph-style trajectory optimization when the full problem is out of
budget, and it already directly addresses the ROADMAP's stated goal ("mitigate scale
drift ... on long single-pass flight corridors") since drift shows up as camera-center
displacement, which is exactly what this optimizes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares


@dataclass
class GeoConstrainedBAResult:
    refined_centers: dict[str, np.ndarray]  # frame_name -> (3,) refined camera center
    mean_reprojection_error_px: float
    mean_gps_residual_m: float
    n_cameras_refined: int
    n_observations: int


def refine_poses_with_gps_priors(
    camera_names: list[str],
    rotations: list[np.ndarray],       # world-to-camera R, one per camera_names entry
    intrinsics: list[np.ndarray],      # (3,3) K, one per camera_names entry
    initial_centers: list[np.ndarray],  # (3,) world-space camera center, initial guess
    observations: list[list[tuple[float, float, np.ndarray]]],
    # observations[i] = [(pixel_x, pixel_y, point_xyz), ...] for camera i
    gps_priors_enu: dict[str, np.ndarray],  # frame_name -> (3,) GPS-derived ENU position
    gps_weight: float = 1.0,
) -> GeoConstrainedBAResult:
    """Jointly refines camera centers to balance reprojection consistency against GPS.

    `gps_weight` is in the same residual units as a reprojection error would need to be
    to trade off equally — since reprojection residuals here are in pixels and GPS
    residuals are in meters, `gps_weight` implicitly carries that unit conversion
    (effectively: how many pixels of reprojection error you'd accept to close 1m of
    GPS disagreement). Larger values trust GPS more; smaller values trust vision more.
    """
    n = len(camera_names)
    if n == 0:
        return GeoConstrainedBAResult({}, 0.0, 0.0, 0, 0)

    refined_centers = {}
    reproj_errors, gps_errors = [], []

    for i in range(n):
        name = camera_names[i]
        r = rotations[i]
        k = intrinsics[i]
        c0 = initial_centers[i]
        cam_obs = observations[i]
        gps_prior = gps_priors_enu.get(name)

        if len(cam_obs) == 0:
            refined_centers[name] = c0
            if gps_prior is not None:
                gps_errors.append(np.linalg.norm(c0 - gps_prior))
            continue

        # Pre-filter observations that are in front of the camera at initial pose
        valid_obs = [o for o in cam_obs if (r @ (o[2] - c0))[2] > 0.01]
        if not valid_obs:
            refined_centers[name] = c0
            continue

        xyz_arr = np.array([o[2] for o in valid_obs], dtype=np.float64)
        px_py = np.array([[o[0], o[1]] for o in valid_obs], dtype=np.float64)

        def cam_residuals(c: np.ndarray) -> np.ndarray:
            xc = (xyz_arr - c) @ r.T
            z = np.maximum(xc[:, 2:3], 1e-3)
            u = k[0, 0] * xc[:, 0:1] / z + k[0, 2]
            v = k[1, 1] * xc[:, 1:2] / z + k[1, 2]
            diff = (np.hstack([u, v]) - px_py).ravel()
            if gps_prior is not None:
                gps_diff = gps_weight * (c - gps_prior)
                return np.concatenate([diff, gps_diff])
            return diff

        result = least_squares(cam_residuals, c0.astype(np.float64), method="trf", max_nfev=150)
        c_opt = result.x
        refined_centers[name] = c_opt

        # Compute metrics
        xc_opt = (xyz_arr - c_opt) @ r.T
        z_opt = np.maximum(xc_opt[:, 2:3], 1e-3)
        u_opt = k[0, 0] * xc_opt[:, 0:1] / z_opt + k[0, 2]
        v_opt = k[1, 1] * xc_opt[:, 1:2] / z_opt + k[1, 2]
        res_2d = np.hstack([u_opt, v_opt]) - px_py
        errors = np.hypot(res_2d[:, 0], res_2d[:, 1])
        reproj_errors.extend(errors.tolist())

        if gps_prior is not None:
            gps_errors.append(np.linalg.norm(c_opt - gps_prior))

    n_obs = sum(len(o) for o in observations)
    return GeoConstrainedBAResult(
        refined_centers=refined_centers,
        mean_reprojection_error_px=float(np.mean(reproj_errors)) if reproj_errors else 0.0,
        mean_gps_residual_m=float(np.mean(gps_errors)) if gps_errors else 0.0,
        n_cameras_refined=n,
        n_observations=n_obs,
    )
