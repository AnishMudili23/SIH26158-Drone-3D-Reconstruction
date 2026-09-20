"""
Phase 3 — Scale + Geo Alignment.

Takes a COLMAP GeometryEstimate (arbitrary-scale camera poses/points) plus the flight's
GPS log (per-frame lat/lon/altitude), and produces a metrically-scaled, georeferenced
point cloud: real-world ENU meters, convertible to lat/lon/altitude via pyproj.

Method: Umeyama similarity alignment (src/common/alignment.py) between the SfM camera
centers (arbitrary units) and their GPS-measured positions (converted to a local ENU
frame anchored at the flight's first GPS fix) — same math validated in Phase 0's
synthetic scale-recovery test (src/feasibility/scale_recovery.py).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyproj

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from common.alignment import umeyama_alignment  # noqa: E402
from common.geometry_interface import CameraPose, GeometryEstimate  # noqa: E402


@dataclass
class GpsFix:
    frame_name: str
    lat: float
    lon: float
    alt_m: float


@dataclass
class GeoAlignedResult:
    points_enu: np.ndarray          # (N, 3) metric ENU meters
    camera_centers_enu: np.ndarray  # (M, 3) metric ENU meters
    aligned_poses: list[CameraPose]  # gravity-aligned extrinsics, world input in meters
    scale_factor: float             # SfM-units -> meters
    origin_lat: float
    origin_lon: float
    origin_alt_m: float
    n_gps_correspondences: int
    mean_alignment_residual_m: float


def _rederive_pose_for_aligned_world(
    pose: CameraPose, scale: float, rotation: np.ndarray, translation: np.ndarray
) -> CameraPose:
    """Re-expresses a camera's extrinsic so it projects points given in the ALIGNED
    (real-world-meters) frame, instead of COLMAP's original arbitrary-scale frame.

    Derivation: alignment maps X_aligned = scale*rotation @ X_orig + translation, so
    X_orig = rotation^T @ (X_aligned - translation) / scale. Substituting into the
    camera's original equation x_cam = R@X_orig + t gives
    R_new = R @ rotation^T / scale,  t_new = t - R_new @ translation.
    x_cam's own units/meaning are unchanged (still whatever COLMAP originally used) —
    only the input world-point's units changed from arbitrary-scale to real meters —
    and standard pinhole projection (pixel = K @ (x_cam / x_cam.z)) is invariant to any
    uniform positive scaling of x_cam, so this is safe to use for projection/homography
    purposes even though R_new is no longer a strictly orthonormal rotation matrix.
    """
    r_new = pose.rotation @ rotation.T / scale
    t_new = pose.translation - r_new @ translation
    return CameraPose(frame_path=pose.frame_path, rotation=r_new, translation=t_new, intrinsics=pose.intrinsics)


_ECEF_FROM_GPS = pyproj.Transformer.from_crs("EPSG:4979", "EPSG:4978", always_xy=True)
_GPS_FROM_ECEF = pyproj.Transformer.from_crs("EPSG:4978", "EPSG:4979", always_xy=True)


def _enu_rotation_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Standard ECEF -> local-ENU rotation matrix at a given geodetic origin."""
    lat, lon = np.radians(lat_deg), np.radians(lon_deg)
    return np.array([
        [-np.sin(lon), np.cos(lon), 0.0],
        [-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)],
        [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)],
    ])


def gps_fixes_to_enu(fixes: list[GpsFix]) -> tuple[np.ndarray, float, float, float]:
    """Converts lat/lon/altitude GPS fixes to a local East-North-Up (ENU) frame anchored
    at the first fix (ARCHITECTURE.md: "standard geodesy approach ... rather than an
    ad-hoc scale-and-shift"). Implemented as ECEF conversion + rotation (textbook ENU
    derivation) rather than proj's "topocentric" pipeline, which proved unreliable
    across proj/pyproj versions for this exact use (mismatched-units pipeline error)."""
    origin = fixes[0]
    origin_ecef = np.array(_ECEF_FROM_GPS.transform(origin.lon, origin.lat, origin.alt_m))
    rot = _enu_rotation_matrix(origin.lat, origin.lon)

    lons = [f.lon for f in fixes]
    lats = [f.lat for f in fixes]
    alts = [f.alt_m for f in fixes]
    x, y, z = _ECEF_FROM_GPS.transform(lons, lats, alts)
    ecef = np.stack([x, y, z], axis=1)

    enu = (rot @ (ecef - origin_ecef).T).T
    return enu, origin.lat, origin.lon, origin.alt_m


def enu_to_gps(points_enu: np.ndarray, origin_lat: float, origin_lon: float, origin_alt_m: float) -> np.ndarray:
    """Inverse of gps_fixes_to_enu — ENU meters back to (lat, lon, alt_m), for exporting
    georeferenced outputs (DSM/DTM, orthomosaic, viewer)."""
    origin_ecef = np.array(_ECEF_FROM_GPS.transform(origin_lon, origin_lat, origin_alt_m))
    rot = _enu_rotation_matrix(origin_lat, origin_lon)
    ecef = (rot.T @ points_enu.T).T + origin_ecef
    lon, lat, alt = _GPS_FROM_ECEF.transform(ecef[:, 0], ecef[:, 1], ecef[:, 2])
    return np.stack([np.array(lat), np.array(lon), np.array(alt)], axis=1)


def lla_to_enu(lat: float, lon: float, alt_m: float, origin_lat: float, origin_lon: float, origin_alt_m: float) -> tuple[float, float, float]:
    """Converts a single geodetic coordinate (lat, lon, alt_m) to local ENU meters relative to origin."""
    origin_ecef = np.array(_ECEF_FROM_GPS.transform(origin_lon, origin_lat, origin_alt_m))
    rot = _enu_rotation_matrix(origin_lat, origin_lon)
    x, y, z = _ECEF_FROM_GPS.transform(lon, lat, alt_m)
    ecef = np.array([x, y, z])
    enu = rot @ (ecef - origin_ecef)
    return float(enu[0]), float(enu[1]), float(enu[2])


def align_geometry_to_gps(geometry: GeometryEstimate, gps_fixes: list[GpsFix]) -> GeoAlignedResult:
    """Match COLMAP poses to GPS fixes by frame filename, align, and rescale the full
    point cloud + camera trajectory into real-world ENU meters."""
    fixes_by_name = {f.frame_name: f for f in gps_fixes}

    matched_sfm_centers = []
    matched_fixes = []
    matched_poses = []
    for pose in geometry.poses:
        name = Path(pose.frame_path).name
        if name in fixes_by_name:
            # Camera center in world coords: C = -R^T @ t (COLMAP stores world-to-camera).
            center = -pose.rotation.T @ pose.translation
            matched_sfm_centers.append(center)
            matched_fixes.append(fixes_by_name[name])
            matched_poses.append(pose)

    if len(matched_sfm_centers) < 3:
        raise ValueError(
            f"Only {len(matched_sfm_centers)} frames had matching GPS fixes — need >= 3 "
            "for a similarity alignment. Check that frame filenames match between the "
            "COLMAP reconstruction and the GPS log."
        )

    sfm_centers = np.array(matched_sfm_centers)
    gps_enu, origin_lat, origin_lon, origin_alt = gps_fixes_to_enu(matched_fixes)

    scale, rotation, translation = umeyama_alignment(sfm_centers, gps_enu)

    aligned_centers = (scale * rotation @ sfm_centers.T).T + translation
    residuals = np.linalg.norm(aligned_centers - gps_enu, axis=1)

    aligned_points = (scale * rotation @ geometry.points_xyz.T).T + translation
    aligned_poses = [
        _rederive_pose_for_aligned_world(pose, scale, rotation, translation) for pose in matched_poses
    ]

    return GeoAlignedResult(
        points_enu=aligned_points,
        camera_centers_enu=aligned_centers,
        aligned_poses=aligned_poses,
        scale_factor=scale,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        origin_alt_m=origin_alt,
        n_gps_correspondences=len(matched_sfm_centers),
        mean_alignment_residual_m=float(residuals.mean()),
    )
