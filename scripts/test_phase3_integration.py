"""
Integration test: real COLMAP-recovered poses + synthetic "GPS" fixes derived from the
known ground-truth camera positions used to render data/datasets/synthetic_3d_scene_cv
(see scripts/generate_synthetic_3d_scene_cv.py's ground_truth_poses.json).

Since that synthetic scene's world coordinates are already in meters (by construction),
its ground-truth camera centers are treated as true ENU positions relative to an
arbitrarily chosen real-world origin (lat/lon), converted to lat/lon "GPS fixes" (with a
small amount of injected noise, matching Phase 0's realistic GPS-noise assumption), then
fed through the REAL Phase 3 alignment (src/geo/scale_alignment.py) against the REAL
COLMAP sparse reconstruction (not synthetic camera matrices, as in tests/test_alignment.py).

Success check: after alignment, COLMAP's recovered+aligned camera centers should land
close to the true camera centers (small residual in meters) — i.e., Phase 2 -> Phase 3
works end-to-end on real (if synthetic-scene) reconstruction output.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from geo.scale_alignment import GpsFix, align_geometry_to_gps, enu_to_gps  # noqa: E402
from reconstruction.colmap_backend import ColmapBackend  # noqa: E402


def run(colmap_work_dir: str, ground_truth_json: str, gps_noise_std_m: float = 1.5, seed: int = 0):
    gt = json.loads(Path(ground_truth_json).read_text())
    gt_by_frame = {p["frame"]: np.array(p["camera_center_world"]) for p in gt["poses"]}

    backend = ColmapBackend()
    sparse_txt_dir = Path(colmap_work_dir) / "sparse_txt"
    if not sparse_txt_dir.exists():
        raise FileNotFoundError(
            f"{sparse_txt_dir} not found — run the Phase 2 sparse reconstruction first."
        )

    from reconstruction.colmap_backend import (  # local import to avoid re-running COLMAP
        _camera_intrinsics,
        _quat_to_rotmat,
        read_sparse_text_model,
    )
    from common.geometry_interface import CameraPose, GeometryEstimate

    model = read_sparse_text_model(sparse_txt_dir)
    poses = []
    for image_id, img in model["images"].items():
        camera = model["cameras"][img["camera_id"]]
        r = _quat_to_rotmat(*img["quat_wxyz"])
        t = np.array(img["translation"])
        k = _camera_intrinsics(camera)
        poses.append(CameraPose(frame_path=img["name"], rotation=r, translation=t, intrinsics=k))

    geometry = GeometryEstimate(
        poses=poses, points_xyz=model["points_xyz"], points_rgb=model["points_rgb"],
        points_confidence=model["track_len"], backend_name="colmap", is_metric_scale=False,
    )
    print(f"COLMAP registered {len(poses)} / {len(gt_by_frame)} frames")

    rng = np.random.default_rng(seed)
    origin_lat, origin_lon, origin_alt = 12.9716, 77.5946, 900.0
    fixes = []
    for pose in poses:
        name = Path(pose.frame_path).name
        if name not in gt_by_frame:
            continue
        true_enu = gt_by_frame[name] + rng.normal(0, gps_noise_std_m, 3)
        lat, lon, alt = enu_to_gps(true_enu[None, :], origin_lat, origin_lon, origin_alt)[0]
        fixes.append(GpsFix(name, lat, lon, alt))

    result = align_geometry_to_gps(geometry, fixes)
    print(f"Aligned using {result.n_gps_correspondences} GPS correspondences")
    print(f"Recovered scale factor (COLMAP units -> meters): {result.scale_factor:.4f}")
    print(f"Mean alignment residual: {result.mean_alignment_residual_m:.3f} m "
          f"(GPS noise injected: {gps_noise_std_m} m std, so this should be roughly that scale)")

    # Direct ground-truth comparison (independent of the GPS-fix noise injected above):
    # compare the ALIGNED camera centers against the true, noiseless camera positions.
    #
    # IMPORTANT: align_geometry_to_gps's ENU frame is anchored at `fixes[0]` (see
    # gps_fixes_to_enu: `origin = fixes[0]`), NOT at the synthetic scene's own world
    # origin (0,0,0) that gt_by_frame's coordinates are expressed in. These are two
    # tangent planes with different anchor points (though ~the same orientation, since
    # Earth curvature is negligible over ~150m) — comparing raw coordinates directly
    # gives a large but entirely spurious constant offset equal to the first frame's own
    # true position (confirmed: an earlier version of this comparison showed a ~85m
    # "error" that exactly matched sqrt(75^2 + 40^2), the distance from the scene origin
    # to frame_0000's position — not a real reconstruction/alignment error at all). Fix:
    # re-anchor both point sets at the first matched frame before comparing.
    true_positions = []
    for pose in poses:
        name = Path(pose.frame_path).name
        if name in gt_by_frame:
            true_positions.append(gt_by_frame[name])
    true_positions = np.array(true_positions)
    true_positions_reanchored = true_positions - true_positions[0]
    aligned_reanchored = result.camera_centers_enu - result.camera_centers_enu[0]

    errors = np.linalg.norm(aligned_reanchored - true_positions_reanchored, axis=1)
    print(f"Error vs. NOISELESS ground truth (both re-anchored at frame 0): "
          f"mean={errors.mean():.3f}m, max={errors.max():.3f}m")
    return result


if __name__ == "__main__":
    run(
        colmap_work_dir=sys.argv[1] if len(sys.argv) > 1 else "outputs/phase2_colmap_test",
        ground_truth_json=sys.argv[2] if len(sys.argv) > 2 else "data/datasets/synthetic_3d_scene_cv/ground_truth_poses.json",
    )
