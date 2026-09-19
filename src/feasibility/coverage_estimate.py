"""
Phase 0 — Single-pass coverage estimate.

Quantifies: flying one continuous drone pass over a scene of buildings + ground, with a
gimbal-tilted camera of realistic FOV, what fraction of the scene's actual surface area
is ever seen by *any* camera in the pass (visible, in-frustum, unoccluded), broken down
by surface type (ground, rooftops, facades)?

This is a from-scratch simulation (no existing library does "drone single-pass coverage
over synthetic buildings") using simple AABB occlusion + frustum + back-face tests,
vectorized with NumPy. Buildings are axis-aligned boxes; ground is the area between them.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class Building:
    cx: float
    cy: float
    half_x: float
    half_y: float
    height: float

    @property
    def box_min(self) -> np.ndarray:
        return np.array([self.cx - self.half_x, self.cy - self.half_y, 0.0])

    @property
    def box_max(self) -> np.ndarray:
        return np.array([self.cx + self.half_x, self.cy + self.half_y, self.height])


def make_synthetic_city(rng: np.random.Generator, area_m: float, n_buildings: int) -> list[Building]:
    buildings = []
    for _ in range(n_buildings):
        cx = rng.uniform(-area_m / 2 + 15, area_m / 2 - 15)
        cy = rng.uniform(-area_m / 2 + 15, area_m / 2 - 15)
        half_x = rng.uniform(4, 12)
        half_y = rng.uniform(4, 12)
        height = rng.uniform(6, 30)
        buildings.append(Building(cx, cy, half_x, half_y, height))
    return buildings


def sample_scene_surface(
    buildings: list[Building], area_m: float, ground_res_m: float, wall_res_m: float
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Returns (points (N,3), normals (N,3), labels) for ground + roofs + walls.

    Ground points under a building footprint are excluded (not real exposed surface).
    """
    points = []
    normals = []
    labels = []

    # Ground grid, minus building footprints.
    grid_1d = np.arange(-area_m / 2, area_m / 2, ground_res_m)
    gx, gy = np.meshgrid(grid_1d, grid_1d)
    gx, gy = gx.ravel(), gy.ravel()
    occupied = np.zeros(gx.shape[0], dtype=bool)
    for b in buildings:
        occupied |= (
            (gx >= b.cx - b.half_x) & (gx <= b.cx + b.half_x)
            & (gy >= b.cy - b.half_y) & (gy <= b.cy + b.half_y)
        )
    free_x, free_y = gx[~occupied], gy[~occupied]
    for x, y in zip(free_x, free_y):
        points.append([x, y, 0.0])
        normals.append([0.0, 0.0, 1.0])
        labels.append("ground")

    # Roofs + 4 walls per building.
    for b in buildings:
        roof_1d_x = np.arange(b.cx - b.half_x, b.cx + b.half_x, ground_res_m)
        roof_1d_y = np.arange(b.cy - b.half_y, b.cy + b.half_y, ground_res_m)
        rx, ry = np.meshgrid(roof_1d_x, roof_1d_y)
        for x, y in zip(rx.ravel(), ry.ravel()):
            points.append([x, y, b.height])
            normals.append([0.0, 0.0, 1.0])
            labels.append("roof")

        wall_z = np.arange(0.0, b.height, wall_res_m)
        # +X wall, -X wall
        wall_y = np.arange(b.cy - b.half_y, b.cy + b.half_y, wall_res_m)
        for z in wall_z:
            for y in wall_y:
                points.append([b.cx + b.half_x, y, z])
                normals.append([1.0, 0.0, 0.0])
                labels.append("facade")
                points.append([b.cx - b.half_x, y, z])
                normals.append([-1.0, 0.0, 0.0])
                labels.append("facade")
        # +Y wall, -Y wall
        wall_x = np.arange(b.cx - b.half_x, b.cx + b.half_x, wall_res_m)
        for z in wall_z:
            for x in wall_x:
                points.append([x, b.cy + b.half_y, z])
                normals.append([0.0, 1.0, 0.0])
                labels.append("facade")
                points.append([x, b.cy - b.half_y, z])
                normals.append([0.0, -1.0, 0.0])
                labels.append("facade")

    return np.array(points), np.array(normals), labels


def make_flight_cameras(
    path_length_m: float,
    altitude_m: float,
    n_positions: int,
    gimbal_pitch_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Straight single-line flight path down the X axis at constant altitude/heading.

    gimbal_pitch_deg: 0 = looking straight down (nadir), 90 = looking at horizon.
    Returns (camera_centers (M,3), view_directions (M,3)) — one fixed gimbal angle
    for the whole pass, matching a single continuous-pass reconnaissance flight
    rather than a nadir-only mapping grid.
    """
    t = np.linspace(0, 1, n_positions)
    x = t * path_length_m - path_length_m / 2
    y = np.zeros(n_positions)
    z = np.full(n_positions, altitude_m)
    centers = np.stack([x, y, z], axis=1)

    pitch = np.radians(gimbal_pitch_deg)
    # Looking mostly down, tilted forward along +X by gimbal_pitch_deg from nadir.
    direction = np.array([np.sin(pitch), 0.0, -np.cos(pitch)])
    directions = np.tile(direction, (n_positions, 1))
    return centers, directions


def ray_aabb_intersect_t(
    origins: np.ndarray, dirs: np.ndarray, box_min: np.ndarray, box_max: np.ndarray
) -> np.ndarray:
    """Vectorized slab-method ray/AABB intersection. Returns entry-t per ray (inf if miss)."""
    inv_dir = np.where(dirs != 0, 1.0 / np.where(dirs != 0, dirs, 1.0), np.inf)
    t1 = (box_min - origins) * inv_dir
    t2 = (box_max - origins) * inv_dir
    tmin = np.minimum(t1, t2)
    tmax = np.maximum(t1, t2)
    t_enter = np.max(tmin, axis=1)
    t_exit = np.min(tmax, axis=1)
    hit = (t_exit >= t_enter) & (t_exit > 1e-6)
    t_enter_out = np.where(hit, t_enter, np.inf)
    return t_enter_out


def compute_visibility(
    points: np.ndarray,
    normals: np.ndarray,
    labels: list[str],
    buildings: list[Building],
    camera_centers: np.ndarray,
    camera_dirs: np.ndarray,
    half_fov_deg: float,
    max_range_m: float,
) -> np.ndarray:
    """Returns bool array: point visible from >=1 camera (frustum + backface + AABB occlusion)."""
    n_points = points.shape[0]
    visible = np.zeros(n_points, dtype=bool)
    cos_half_fov = np.cos(np.radians(half_fov_deg))
    eps = 1e-3

    box_mins = np.array([b.box_min for b in buildings])
    box_maxs = np.array([b.box_max for b in buildings])

    for cam_idx in range(camera_centers.shape[0]):
        remaining = ~visible
        if not remaining.any():
            break
        idx = np.where(remaining)[0]
        p = points[idx]
        n = normals[idx]

        cam = camera_centers[cam_idx]
        view_dir = camera_dirs[cam_idx]

        to_cam = cam[None, :] - p
        dist = np.linalg.norm(to_cam, axis=1)
        dist_safe = np.where(dist > 1e-9, dist, 1e-9)
        to_cam_unit = to_cam / dist_safe[:, None]

        in_range = dist <= max_range_m
        backface_ok = np.einsum("ij,ij->i", n, to_cam_unit) > 0.05
        ray_from_cam = -to_cam_unit
        frustum_ok = np.einsum("j,ij->i", view_dir, ray_from_cam) >= cos_half_fov

        candidate = in_range & backface_ok & frustum_ok
        if not candidate.any():
            continue

        cand_idx = np.where(candidate)[0]
        origins = p[cand_idx] + n[cand_idx] * eps
        dirs = to_cam_unit[cand_idx]
        seg_len = dist_safe[cand_idx] - eps

        occluded = np.zeros(cand_idx.shape[0], dtype=bool)
        for b_min, b_max in zip(box_mins, box_maxs):
            t_hit = ray_aabb_intersect_t(origins, dirs, b_min, b_max)
            occluded |= t_hit < (seg_len - 1e-2)

        newly_visible = cand_idx[~occluded]
        global_idx = idx[newly_visible]
        visible[global_idx] = True

    return visible


@dataclass
class CoverageResult:
    n_buildings: int
    path_length_m: float
    altitude_m: float
    gimbal_pitch_deg: float
    half_fov_deg: float
    n_camera_positions: int
    coverage_pct_overall: float
    coverage_pct_by_class: dict


def run_coverage_estimate(seed: int = 7) -> CoverageResult:
    rng = np.random.default_rng(seed)
    area_m = 250.0
    buildings = make_synthetic_city(rng, area_m=area_m, n_buildings=18)
    points, normals, labels = sample_scene_surface(
        buildings, area_m=area_m, ground_res_m=3.0, wall_res_m=2.0
    )
    labels = np.array(labels)

    centers, dirs = make_flight_cameras(
        path_length_m=220.0, altitude_m=80.0, n_positions=120, gimbal_pitch_deg=25.0
    )

    visible = compute_visibility(
        points, normals, labels, buildings, centers, dirs,
        half_fov_deg=35.0,  # ~70 deg full FOV, typical consumer drone camera
        max_range_m=180.0,
    )

    overall_pct = float(visible.mean() * 100.0)
    by_class = {}
    for cls in np.unique(labels):
        mask = labels == cls
        by_class[str(cls)] = float(visible[mask].mean() * 100.0) if mask.any() else None

    return CoverageResult(
        n_buildings=len(buildings),
        path_length_m=220.0,
        altitude_m=80.0,
        gimbal_pitch_deg=25.0,
        half_fov_deg=35.0,
        n_camera_positions=120,
        coverage_pct_overall=overall_pct,
        coverage_pct_by_class=by_class,
    )


if __name__ == "__main__":
    result = run_coverage_estimate()
    print(json.dumps(asdict(result), indent=2))
