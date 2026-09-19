"""
Generates a synthetic multi-view drone-flight image set with real 3D parallax and
occlusion, using pure OpenCV homography warping instead of a full 3D renderer.

(Open3D's OffscreenRenderer was tried first but proved unreliable in this environment —
render_to_image() intermittently returned black/stale frames with no dependable warm-up
signal, confirmed by direct experiment across multiple mitigation attempts. This CV-only
approach reuses the same ground-plane homography math already validated in
src/exports/orthomosaic.py, run in the opposite direction: instead of un-warping camera
images onto a world-plane canvas, we warp world-plane textures INTO each camera's image.)

Scene = one large ground texture (z=0) + several buildings, each a single "front wall"
vertical-plane texture (facing the flight line) + a roof texture, all rich random-noise
patterns for SIFT-friendly texture. For each camera pose, every plane's world-to-image
homography is computed analytically and composited back-to-front (painter's algorithm,
sorted by camera-space depth) so nearer buildings correctly occlude farther ground/
buildings — giving genuine multi-view parallax and occlusion for a real COLMAP test,
without depending on a flaky external renderer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reconstruction.colmap_backend import _quat_to_rotmat  # noqa: E402 (unused here, kept for parity)


def make_rich_texture(rng: np.random.Generator, size: int, base_color: np.ndarray) -> np.ndarray:
    """A checkerboard + speckle-noise texture — plenty of local gradient/contrast for
    SIFT, cheap alternative to a real photo texture."""
    tex = np.zeros((size, size, 3), dtype=np.float64)
    cell = max(4, size // 24)
    for gy in range(0, size, cell):
        for gx in range(0, size, cell):
            shade = 0.85 if ((gx // cell) + (gy // cell)) % 2 == 0 else 1.15
            tex[gy:gy + cell, gx:gx + cell] = base_color * shade
    noise = rng.uniform(-25, 25, tex.shape)
    tex = np.clip(tex * 255 + noise, 0, 255).astype(np.uint8)
    return tex


def plane_world_to_image_homography(
    origin: np.ndarray, e1: np.ndarray, e2: np.ndarray, width_m: float, height_m: float,
    tex_w: int, tex_h: int, r: np.ndarray, t: np.ndarray, k: np.ndarray,
) -> np.ndarray:
    """Texture-pixel (px, py, 1) -> image-pixel homogeneous homography, for a world
    plane through `origin` spanned by unit vectors e1 (+px direction), e2 (+py
    direction), physically `width_m` x `height_m`, rendered from a `tex_w` x `tex_h`
    texture image.

    Derivation: any point on the plane is P = origin + (px/tex_w)*width_m*e1 +
    (py/tex_h)*height_m*e2. Camera projection is linear in P (homogeneous): image_pixel
    ~ K @ (R @ P + t). Substituting P's affine form in (px, py, 1) gives a 3x3 matrix
    directly usable as the `M` argument to cv2.warpPerspective(src=texture, M, dsize)
    (confirmed empirically: warpPerspective's M maps src pixel coords -> dst pixel
    coords, the forward direction, not backward).
    """
    col1 = k @ (r @ (e1 * (width_m / tex_w)))
    col2 = k @ (r @ (e2 * (height_m / tex_h)))
    col3 = k @ (r @ origin + t)
    return np.column_stack([col1, col2, col3])


def composite_plane(
    canvas: np.ndarray, texture: np.ndarray, homography: np.ndarray, canvas_size: tuple[int, int]
) -> None:
    warped = cv2.warpPerspective(
        texture, homography, canvas_size, flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )
    mask = cv2.warpPerspective(
        np.full(texture.shape[:2], 255, dtype=np.uint8), homography, canvas_size,
        flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    ) > 0
    canvas[mask] = warped[mask]


def make_scene_planes(rng: np.random.Generator, area_m: float, n_buildings: int):
    """Returns a list of dicts: {origin, e1, e2, width_m, height_m, texture, depth_ref}."""
    planes = []
    ground_tex = make_rich_texture(rng, 1024, np.array([0.35, 0.45, 0.3]))
    planes.append({
        "origin": np.array([-area_m / 2, -area_m / 2, 0.0]),
        "e1": np.array([1.0, 0.0, 0.0]), "e2": np.array([0.0, 1.0, 0.0]),
        "width_m": area_m, "height_m": area_m, "texture": ground_tex,
    })

    for _ in range(n_buildings):
        cx = rng.uniform(-area_m / 2 + 10, area_m / 2 - 10)
        cy = rng.uniform(5, area_m / 2 - 10)  # keep buildings on +Y side, facing flight line at y=0
        half_x = rng.uniform(4, 9)
        height = rng.uniform(6, 16)
        color = rng.uniform(0.3, 0.7, 3)

        wall_tex = make_rich_texture(rng, 512, color)
        planes.append({
            "origin": np.array([cx - half_x, cy, 0.0]),
            "e1": np.array([1.0, 0.0, 0.0]), "e2": np.array([0.0, 0.0, 1.0]),
            "width_m": 2 * half_x, "height_m": height, "texture": wall_tex,
        })
        roof_tex = make_rich_texture(rng, 256, color * 1.1)
        planes.append({
            "origin": np.array([cx - half_x, cy - half_x, height]),
            "e1": np.array([1.0, 0.0, 0.0]), "e2": np.array([0.0, -1.0, 0.0]),
            "width_m": 2 * half_x, "height_m": 2 * half_x, "texture": roof_tex,
        })
    return planes


def make_flight_poses(n_frames: int, path_length_m: float, altitude_m: float, pitch_deg: float):
    poses = []
    t_arr = np.linspace(0, 1, n_frames)
    for tt in t_arr:
        cx = tt * path_length_m - path_length_m / 2
        c = np.array([cx, 0.0, altitude_m])
        pitch = np.radians(pitch_deg)
        forward = np.array([0.0, np.sin(pitch), -np.cos(pitch)])  # tilt toward +Y (buildings)
        world_up = np.array([0.0, 0.0, 1.0])
        right = np.cross(forward, world_up)
        right /= np.linalg.norm(right)
        cam_up = np.cross(right, forward)
        r = np.stack([right, -cam_up, forward], axis=0)
        t = -r @ c
        poses.append((r, t, c))
    return poses


def render_sequence(
    out_dir: str, n_frames: int = 60, width: int = 640, height: int = 480,
    path_length_m: float = 150.0, altitude_m: float = 40.0, pitch_deg: float = 35.0,
    area_m: float = 120.0, n_buildings: int = 10, seed: int = 0,
):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    planes = make_scene_planes(rng, area_m, n_buildings)
    poses = make_flight_poses(n_frames, path_length_m, altitude_m, pitch_deg)

    fx = fy = width
    cx_p, cy_p = width / 2, height / 2
    k = np.array([[fx, 0, cx_p], [0, fy, cy_p], [0, 0, 1]])

    manifest = []
    for i, (r, t, c) in enumerate(poses):
        canvas = np.full((height, width, 3), (140, 110, 80), dtype=np.uint8)  # sky-ish fallback

        plane_depths = []
        for plane in planes:
            plane_center = plane["origin"] + plane["e1"] * plane["width_m"] / 2 + plane["e2"] * plane["height_m"] / 2
            depth = (r @ plane_center + t)[2]
            plane_depths.append(depth)
        order = np.argsort(plane_depths)[::-1]  # far to near

        for idx in order:
            plane = planes[idx]
            tex = plane["texture"]
            h_mat = plane_world_to_image_homography(
                plane["origin"], plane["e1"], plane["e2"], plane["width_m"], plane["height_m"],
                tex.shape[1], tex.shape[0], r, t, k,
            )
            composite_plane(canvas, tex, h_mat, (width, height))

        frame_path = out_dir / f"frame_{i:04d}.jpg"
        cv2.imwrite(str(frame_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
        manifest.append({
            "frame": frame_path.name,
            "camera_center_world": c.tolist(),
            "rotation_world_to_cam": r.tolist(),
            "translation_world_to_cam": t.tolist(),
        })

    (out_dir / "ground_truth_poses.json").write_text(json.dumps({
        "intrinsics": {"fx": fx, "fy": fy, "cx": cx_p, "cy": cy_p, "width": width, "height": height},
        "poses": manifest,
    }, indent=2))
    print(f"Rendered {n_frames} frames to {out_dir}")
    return out_dir


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/datasets/synthetic_3d_scene_cv"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    render_sequence(out, n_frames=n)
