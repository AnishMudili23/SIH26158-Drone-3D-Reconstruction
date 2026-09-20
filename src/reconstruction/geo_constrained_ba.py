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

    x0 = np.concatenate([c.astype(np.float64) for c in initial_centers])

    def residuals(x: np.ndarray) -> np.ndarray:
        centers = x.reshape(n, 3)
        res = []
        for i in range(n):
            r, k, c = rotations[i], intrinsics[i], centers[i]
            for px, py, xyz in observations[i]:
                x_cam = r @ (xyz - c)
                if x_cam[2] <= 1e-6:
                    continue
                proj = k @ x_cam
                u, v = proj[0] / proj[2], proj[1] / proj[2]
                res.append(u - px)
                res.append(v - py)
            name = camera_names[i]
            if name in gps_priors_enu:
                res.extend((gps_weight * (centers[i] - gps_priors_enu[name])).tolist())
        return np.array(res) if res else np.zeros(1)

    result = least_squares(residuals, x0, method="trf", max_nfev=2000)
    refined = result.x.reshape(n, 3)

    reproj_errors, gps_errors = [], []
    for i in range(n):
        r, k, c = rotations[i], intrinsics[i], refined[i]
        for px, py, xyz in observations[i]:
            x_cam = r @ (xyz - c)
            if x_cam[2] <= 1e-6:
                continue
            proj = k @ x_cam
            u, v = proj[0] / proj[2], proj[1] / proj[2]
            reproj_errors.append(np.hypot(u - px, v - py))
        name = camera_names[i]
        if name in gps_priors_enu:
            gps_errors.append(np.linalg.norm(refined[i] - gps_priors_enu[name]))

    n_obs = sum(len(o) for o in observations)
    return GeoConstrainedBAResult(
        refined_centers={camera_names[i]: refined[i] for i in range(n)},
        mean_reprojection_error_px=float(np.mean(reproj_errors)) if reproj_errors else 0.0,
        mean_gps_residual_m=float(np.mean(gps_errors)) if gps_errors else 0.0,
        n_cameras_refined=n,
        n_observations=n_obs,
    )
