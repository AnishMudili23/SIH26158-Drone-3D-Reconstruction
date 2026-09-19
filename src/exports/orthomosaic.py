"""
Phase 7 — Orthomosaic Export: stitch a top-down 2D map from frames + COLMAP camera
poses (ARCHITECTURE.md's Orthomosaic Export component; TECH_STACK.md: "OpenCV
(homography stitching), uses existing frames + camera poses from COLMAP").

Since each frame's camera pose (R, t, K) is already known from COLMAP, stitching does
not need feature-based image matching (cv2.Stitcher) — we can derive an exact planar
homography per frame analytically, assuming a single representative ground elevation
z_ref (a flat-ground approximation; genuine terrain relief will show as perspective
distortion in the ortho, same limitation every fast orthomosaic tool has without a true
ortho-rectification DEM pass).

For a 3D point (X, Y, z_ref) on the assumed ground plane:
    image_px ~ K @ (R @ [X, Y, z_ref] + t)
             = K @ [R[:,0], R[:,1], R[:,2]*z_ref + t] @ [X, Y, 1]
so H = K @ [R[:,0], R[:,1], R[:,2]*z_ref + t] is a 3x3 homography mapping ground-plane
world coordinates -> image pixels. Composed with world->ortho-pixel affine mapping and
inverted, this feeds directly into cv2.warpPerspective — no dense per-pixel raycasting
needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from common.geometry_interface import CameraPose  # noqa: E402


def estimate_ground_z_ref(
    points_xyz: np.ndarray,
    class_names: list[str] | None = None,
    ground_like_classes: tuple[str, ...] = ("Road", "Background clutter"),
) -> float:
    """Picks a representative flat-ground elevation for the orthomosaic homography.

    Using the median of *all* points is a bad default when the cloud is dominated by
    elevated features (buildings, trees) rather than ground — confirmed by direct
    experiment: on a real reconstruction that was ~95% building points, the naive
    all-point median landed near roof height, so nearly every camera's ground-plane
    homography projected outside its actual image bounds, and the resulting
    orthomosaic was almost entirely black (0.7% coverage) except a sliver where a
    camera happened to be pointed steeply enough to still intersect that (wrong)
    plane. Restricting to the same ground-like class proxy DSM/DTM export already uses
    (Road, Background clutter) fixes this. Falls back to the all-point median only if
    no ground-like points exist (better than crashing, though callers should treat
    that fallback result with suspicion).
    """
    if class_names is not None:
        ground_mask = np.array([c in ground_like_classes for c in class_names])
        if ground_mask.any():
            return float(np.median(points_xyz[ground_mask, 2]))
    return float(np.median(points_xyz[:, 2]))


def ground_plane_homography(pose: CameraPose, z_ref: float) -> np.ndarray:
    r, t, k = pose.rotation, pose.translation, pose.intrinsics
    plane_basis = np.column_stack([r[:, 0], r[:, 1], r[:, 2] * z_ref + t])
    return k @ plane_basis


def world_to_ortho_pixel_affine(x_min: float, y_max: float, gsd_m: float) -> np.ndarray:
    """World (X, Y) meters -> ortho raster (col, row) pixel indices."""
    return np.array([
        [1.0 / gsd_m, 0.0, -x_min / gsd_m],
        [0.0, -1.0 / gsd_m, y_max / gsd_m],
        [0.0, 0.0, 1.0],
    ])


def build_orthomosaic(
    poses: list[CameraPose],
    image_dir: str | Path,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    z_ref: float,
    gsd_m: float = 0.2,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (ortho_bgr uint8 (H,W,3), coverage_count (H,W) int) — average-blended
    across all frames whose ground-plane homography places them inside the canvas."""
    width = max(1, int(np.ceil((x_max - x_min) / gsd_m)))
    height = max(1, int(np.ceil((y_max - y_min) / gsd_m)))

    accum = np.zeros((height, width, 3), dtype=np.float64)
    count = np.zeros((height, width), dtype=np.int32)

    world_to_ortho = world_to_ortho_pixel_affine(x_min, y_max, gsd_m)

    for pose in poses:
        image_path = Path(image_dir) / Path(pose.frame_path).name
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        h_world_to_image = ground_plane_homography(pose, z_ref)
        try:
            h_image_to_world = np.linalg.inv(h_world_to_image)
        except np.linalg.LinAlgError:
            continue

        m_image_to_ortho = world_to_ortho @ h_image_to_world

        warped = cv2.warpPerspective(
            image.astype(np.float64), m_image_to_ortho, (width, height),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
        )
        mask = cv2.warpPerspective(
            np.ones(image.shape[:2], dtype=np.uint8) * 255, m_image_to_ortho, (width, height),
            flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
        ) > 0

        accum[mask] += warped[mask]
        count[mask] += 1

    with np.errstate(invalid="ignore", divide="ignore"):
        ortho = np.where(count[..., None] > 0, accum / np.maximum(count[..., None], 1), 0)
    return ortho.astype(np.uint8), count
