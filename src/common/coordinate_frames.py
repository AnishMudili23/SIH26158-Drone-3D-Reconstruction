"""
Unified coordinate-frame contract and canonical similarity transformations.

Defines the core spatial reference frames:
- SFM: Arbitrary-scale camera/point coordinate frame from Structure-from-Motion (e.g. COLMAP).
- LOCAL_METRIC: Scaled metric coordinates in local visual frame (meters, no geodetic anchor).
- ENU: East-North-Up local tangent plane in real-world meters anchored at (lat0, lon0, alt0).
- WGS84: Geodetic coordinates (lat, lon, alt_m) in EPSG:4979.
- UTM: Universal Transverse Mercator projected coordinates (meters) in local UTM zone.

Rule: Every exported 3D object / reconstruction result must declare its coordinate frame.
No component gets to implement its own coordinate conversion.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING
import numpy as np
import pyproj

if TYPE_CHECKING:
    from common.geometry_interface import CameraPose


class CoordinateFrame(str, Enum):
    SFM = "SFM"
    LOCAL_METRIC = "LOCAL_METRIC"
    ENU = "ENU"
    WGS84 = "WGS84"
    UTM = "UTM"


@dataclass
class SimilarityTransform:
    """Canonical similarity transformation mapping points from source to target frame:
    
    X_dst = scale * (rotation @ X_src.T).T + translation
    
    where rotation is strictly orthonormal (3, 3) with det(R) = +1,
    scale is a positive scalar, and translation is a (3,) vector in the target frame.
    """
    scale: float
    rotation: np.ndarray      # (3, 3) orthonormal rotation matrix
    translation: np.ndarray   # (3,) translation in target frame

    def __post_init__(self):
        self.scale = float(self.scale)
        self.rotation = np.asarray(self.rotation, dtype=np.float64)
        self.translation = np.asarray(self.translation, dtype=np.float64).reshape(3)
        assert self.rotation.shape == (3, 3), f"Expected (3,3) rotation, got {self.rotation.shape}"

    def transform_points(self, points: np.ndarray) -> np.ndarray:
        """Transforms (N, 3) or (3,) points: scale * (rotation @ points.T).T + translation"""
        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim == 1:
            return self.scale * (self.rotation @ pts) + self.translation
        if len(pts) == 0:
            return pts.copy()
        return (self.scale * (self.rotation @ pts.T)).T + self.translation

    def transform_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """Transforms directional vectors or normals (rotation only, invariant to translation/scale)."""
        vecs = np.asarray(vectors, dtype=np.float64)
        if vecs.ndim == 1:
            return self.rotation @ vecs
        if len(vecs) == 0:
            return vecs.copy()
        return (self.rotation @ vecs.T).T

    def transform_camera_center(self, center: np.ndarray) -> np.ndarray:
        """Transforms a 3D camera center point into the target frame."""
        c = np.asarray(center, dtype=np.float64).reshape(3)
        return self.scale * (self.rotation @ c) + self.translation

    def inverse(self) -> SimilarityTransform:
        """Returns the exact inverse similarity transform:
        X_src = (1/scale) * rotation.T @ (X_dst - translation)
        """
        inv_scale = 1.0 / self.scale if self.scale != 0 else 1.0
        inv_rot = self.rotation.T
        inv_trans = -inv_scale * (inv_rot @ self.translation)
        return SimilarityTransform(scale=inv_scale, rotation=inv_rot, translation=inv_trans)

    @classmethod
    def identity(cls) -> SimilarityTransform:
        """Identity transform (no scaling, identity rotation, zero translation)."""
        return cls(scale=1.0, rotation=np.eye(3, dtype=np.float64), translation=np.zeros(3, dtype=np.float64))


@dataclass
class CameraTrajectoryENU:
    """Georeferenced camera pose in real-world metric ENU coordinates.
    
    Preserves strict separation between:
    - C_enu: Physical camera center in ENU meters.
    - rotation: Strictly orthonormal (3, 3) world-to-camera orientation matrix.
    - translation: Metric world-to-camera translation: t = -R @ C_enu.
    """
    frame_path: str
    center_enu: np.ndarray        # (3,) camera center in ENU meters
    rotation: np.ndarray          # (3, 3) orthonormal world-to-camera rotation
    intrinsics: np.ndarray        # (3, 3) camera intrinsic matrix
    coordinate_frame: CoordinateFrame = CoordinateFrame.ENU

    def __post_init__(self):
        self.center_enu = np.asarray(self.center_enu, dtype=np.float64).reshape(3)
        self.rotation = np.asarray(self.rotation, dtype=np.float64).reshape((3, 3))
        self.intrinsics = np.asarray(self.intrinsics, dtype=np.float64).reshape((3, 3))

    @property
    def translation(self) -> np.ndarray:
        """Metric world-to-camera translation: t = -R @ C_enu"""
        return -self.rotation @ self.center_enu

    def project_point(self, point_enu: np.ndarray) -> np.ndarray:
        """Projects an ENU world point to 2D image coordinates (u, v)."""
        return project_world_point(point_enu, self.center_enu, self.rotation, self.intrinsics)

    def to_camera_pose(self) -> CameraPose:
        from common.geometry_interface import CameraPose
        return CameraPose(
            frame_path=self.frame_path,
            rotation=self.rotation,
            translation=self.translation,
            intrinsics=self.intrinsics,
            coordinate_frame=self.coordinate_frame,
        )


# Global geodesic transformers
_ECEF_FROM_GPS = pyproj.Transformer.from_crs("EPSG:4979", "EPSG:4978", always_xy=True)
_GPS_FROM_ECEF = pyproj.Transformer.from_crs("EPSG:4978", "EPSG:4979", always_xy=True)


def enu_rotation_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Standard ECEF -> local-ENU rotation matrix at a given geodetic origin."""
    lat, lon = np.radians(lat_deg), np.radians(lon_deg)
    return np.array([
        [-np.sin(lon), np.cos(lon), 0.0],
        [-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)],
        [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)],
    ], dtype=np.float64)


def wgs84_to_enu(
    lats: np.ndarray | list[float] | float,
    lons: np.ndarray | list[float] | float,
    alts: np.ndarray | list[float] | float,
    origin_lat: float,
    origin_lon: float,
    origin_alt: float,
) -> np.ndarray:
    """Converts WGS84 geodetic coordinates to local ENU meters relative to origin.
    Returns (N, 3) or (3,) array.
    """
    is_scalar = np.isscalar(lats)
    lats_arr = np.atleast_1d(np.asarray(lats, dtype=np.float64))
    lons_arr = np.atleast_1d(np.asarray(lons, dtype=np.float64))
    alts_arr = np.atleast_1d(np.asarray(alts, dtype=np.float64))

    origin_ecef = np.array(_ECEF_FROM_GPS.transform(origin_lon, origin_lat, origin_alt), dtype=np.float64)
    rot = enu_rotation_matrix(origin_lat, origin_lon)

    x, y, z = _ECEF_FROM_GPS.transform(lons_arr, lats_arr, alts_arr)
    ecef = np.stack([x, y, z], axis=1)
    enu = (rot @ (ecef - origin_ecef).T).T
    return enu[0] if is_scalar else enu


def enu_to_wgs84(
    points_enu: np.ndarray,
    origin_lat: float,
    origin_lon: float,
    origin_alt: float,
) -> np.ndarray:
    """Converts local ENU meters back to geodetic WGS84 (lat, lon, alt_m).
    Returns (N, 3) or (3,) array in [lat, lon, alt] order.
    """
    pts = np.asarray(points_enu, dtype=np.float64)
    is_1d = pts.ndim == 1
    pts_2d = pts.reshape(-1, 3)

    origin_ecef = np.array(_ECEF_FROM_GPS.transform(origin_lon, origin_lat, origin_alt), dtype=np.float64)
    rot = enu_rotation_matrix(origin_lat, origin_lon)

    ecef = (rot.T @ pts_2d.T).T + origin_ecef
    lon, lat, alt = _GPS_FROM_ECEF.transform(ecef[:, 0], ecef[:, 1], ecef[:, 2])
    wgs84 = np.stack([lat, lon, alt], axis=1)
    return wgs84[0] if is_1d else wgs84


def wgs84_to_utm(lat: float, lon: float, alt_m: float) -> tuple[np.ndarray, int]:
    """Converts a single or multiple WGS84 coordinates to UTM (easting, northing, alt_m, utm_epsg)."""
    zone_num = int((lon + 180) // 6) + 1
    is_northern = lat >= 0
    epsg_code = (32600 if is_northern else 32700) + zone_num
    transformer = pyproj.Transformer.from_crs("EPSG:4979", f"EPSG:{epsg_code}", always_xy=True)
    easting, northing, alt = transformer.transform(lon, lat, alt_m)
    return np.array([easting, northing, alt], dtype=np.float64), epsg_code


def enu_to_utm(
    points_enu: np.ndarray,
    origin_lat: float,
    origin_lon: float,
    origin_alt: float,
) -> tuple[np.ndarray, int]:
    """Converts ENU points to UTM through origin geodetic anchor."""
    wgs = enu_to_wgs84(points_enu, origin_lat, origin_lon, origin_alt)
    is_1d = wgs.ndim == 1
    wgs_2d = wgs.reshape(-1, 3)
    zone_num = int((origin_lon + 180) // 6) + 1
    epsg_code = (32600 if origin_lat >= 0 else 32700) + zone_num
    transformer = pyproj.Transformer.from_crs("EPSG:4979", f"EPSG:{epsg_code}", always_xy=True)
    easting, northing, alt = transformer.transform(wgs_2d[:, 1], wgs_2d[:, 0], wgs_2d[:, 2])
    utm = np.stack([easting, northing, alt], axis=1)
    return (utm[0] if is_1d else utm), epsg_code


def sfm_to_enu(points_sfm: np.ndarray, transform: SimilarityTransform) -> np.ndarray:
    """Explicitly converts points from arbitrary SfM scale to metric ENU frame."""
    return transform.transform_points(points_sfm)


def enu_to_sfm(points_enu: np.ndarray, transform: SimilarityTransform) -> np.ndarray:
    """Explicitly converts points from ENU frame back to SfM frame."""
    return transform.inverse().transform_points(points_enu)


def project_world_point(
    point_world: np.ndarray,
    camera_center_world: np.ndarray,
    camera_rotation: np.ndarray,
    K: np.ndarray,
) -> np.ndarray:
    """Projects a 3D world point into pixel coordinates via standard pinhole camera projection.
    
    p_cam = R @ (point_world - camera_center_world)
    pixel = K @ (p_cam / p_cam[2])
    
    Guarantees projection without mutating camera rotation into non-orthonormal matrices.
    """
    pt = np.asarray(point_world, dtype=np.float64).reshape(3)
    c = np.asarray(camera_center_world, dtype=np.float64).reshape(3)
    R = np.asarray(camera_rotation, dtype=np.float64).reshape((3, 3))
    K_mat = np.asarray(K, dtype=np.float64).reshape((3, 3))

    p_cam = R @ (pt - c)
    if p_cam[2] <= 1e-6:
        return np.array([np.nan, np.nan])
    p_pix = K_mat @ (p_cam / p_cam[2])
    return p_pix[:2]
