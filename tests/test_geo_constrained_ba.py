import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reconstruction.geo_constrained_ba import refine_poses_with_gps_priors


def _synthetic_scene(n_cameras=8, n_points=40, seed=0):
    rng = np.random.default_rng(seed)
    k = np.array([[800.0, 0.0, 320.0], [0.0, 800.0, 240.0], [0.0, 0.0, 1.0]])
    r_identity = np.eye(3)

    true_centers = np.stack([np.linspace(0, 70, n_cameras), np.zeros(n_cameras), np.zeros(n_cameras)], axis=1)
    # Points at z in [30, 50] are in front of a camera at z=0 with identity rotation
    # (x_cam.z = point.z - camera.z > 0), matching pinhole's +Z-forward convention.
    points_xyz = rng.uniform(low=[0, -20, 30], high=[70, 20, 50], size=(n_points, 3))

    observations = []
    for i in range(n_cameras):
        obs = []
        c = true_centers[i]
        for xyz in points_xyz:
            x_cam = r_identity @ (xyz - c)
            if x_cam[2] <= 1.0:
                continue
            proj = k @ x_cam
            u, v = proj[0] / proj[2], proj[1] / proj[2]
            if 0 <= u <= 640 and 0 <= v <= 480:
                obs.append((u, v, xyz))
        observations.append(obs)

    return k, r_identity, true_centers, observations


def test_gps_prior_pulls_drifted_cameras_back_toward_truth():
    k, r_identity, true_centers, observations = _synthetic_scene()
    n = len(true_centers)
    camera_names = [f"frame_{i:03d}" for i in range(n)]
    rotations = [r_identity] * n
    intrinsics = [k] * n

    # Simulate COLMAP-style smooth translation drift (e.g. unmodeled scale creep)
    rng = np.random.default_rng(1)
    drift = np.linspace(0, 3.0, n)[:, None] * np.array([0.0, 1.0, 0.0])
    drifted_centers = [true_centers[i] + drift[i] for i in range(n)]

    initial_gps_error = np.mean([np.linalg.norm(drifted_centers[i] - true_centers[i]) for i in range(n)])
    assert initial_gps_error > 0.5  # sanity check the drift is meaningful

    gps_priors = {camera_names[i]: true_centers[i] + rng.normal(0, 0.05, size=3) for i in range(n)}

    result = refine_poses_with_gps_priors(
        camera_names=camera_names,
        rotations=rotations,
        intrinsics=intrinsics,
        initial_centers=drifted_centers,
        observations=observations,
        gps_priors_enu=gps_priors,
        gps_weight=50.0,  # strongly trust GPS over reprojection here
    )

    refined_error = np.mean([
        np.linalg.norm(result.refined_centers[camera_names[i]] - true_centers[i]) for i in range(n)
    ])
    assert refined_error < initial_gps_error * 0.5, (
        f"Expected GPS-constrained refinement to reduce drift; before={initial_gps_error:.3f}m "
        f"after={refined_error:.3f}m"
    )
    assert result.n_cameras_refined == n
    assert result.n_observations > 0


def test_zero_gps_weight_leaves_reprojection_consistent_solution_near_initial():
    k, r_identity, true_centers, observations = _synthetic_scene(n_cameras=5, n_points=30)
    n = len(true_centers)
    camera_names = [f"frame_{i:03d}" for i in range(n)]
    rotations = [r_identity] * n
    intrinsics = [k] * n

    # No drift, no GPS priors at all -> refinement should leave cameras essentially unchanged
    result = refine_poses_with_gps_priors(
        camera_names=camera_names,
        rotations=rotations,
        intrinsics=intrinsics,
        initial_centers=list(true_centers),
        observations=observations,
        gps_priors_enu={},
        gps_weight=10.0,
    )
    for i in range(n):
        assert np.linalg.norm(result.refined_centers[camera_names[i]] - true_centers[i]) < 1e-3
    assert result.mean_reprojection_error_px < 1e-3
