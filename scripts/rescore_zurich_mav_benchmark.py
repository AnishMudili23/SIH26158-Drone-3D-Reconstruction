"""Corrected ground-truth scoring for the already-completed Zurich MAV COLMAP run.

The first run (run_zurich_mav_benchmark.py) had a real bug: it loaded the dataset's
surveyed UTM ground-truth checkpoints (GroundTruthCheckpoint.utm_x/y/z) but then never
actually used them — it compared reconstructed camera positions against each frame's
own onboard GPS reading instead (the wrong comparison; that's close to circular since
alignment was already fit to that same GPS). This script re-does only the fast steps
(outlier removal + GPS alignment + scoring) against the cached COLMAP sparse model,
this time correctly converting the surveyed UTM32N ground truth to the same ENU frame
via pyproj before comparing. No need to re-run the 51-minute COLMAP reconstruction.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyproj

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from datasets.zurich_mav import load_zurich_mav_session  # noqa: E402
from reconstruction.colmap_backend import read_sparse_text_model, _quat_to_rotmat, _camera_intrinsics  # noqa: E402
from common.geometry_interface import CameraPose, GeometryEstimate  # noqa: E402
from pointcloud.outlier_removal import remove_statistical_outliers  # noqa: E402
from geo.scale_alignment import GpsFix, align_geometry_to_gps, lla_to_enu  # noqa: E402
from accuracy.georeference_accuracy import compute_georeference_accuracy  # noqa: E402

UTM32N_TO_WGS84 = pyproj.Transformer.from_crs("EPSG:32632", "EPSG:4979", always_xy=True)


def main():
    dataset_dir = "datasets/zurich_mav/AGZ_subset"
    sparse_txt_dir = "outputs/zurich_mav_benchmark/reconstruction/sparse_txt"
    output_dir = Path("outputs/zurich_mav_benchmark")

    session, image_paths, gt_checkpoints = load_zurich_mav_session(dataset_dir)
    frame_by_name = {f.image_filename: f for f in session.frames}

    sparse_model = read_sparse_text_model(sparse_txt_dir)
    poses = []
    for image_id, img in sparse_model["images"].items():
        r = _quat_to_rotmat(*img["quat_wxyz"])
        t = np.array(img["translation"])
        k = _camera_intrinsics(sparse_model["cameras"][img["camera_id"]])
        poses.append(CameraPose(frame_path=img["name"], rotation=r, translation=t, intrinsics=k))

    outlier_mask, _ = remove_statistical_outliers(sparse_model["points_xyz"], nb_neighbors=20, std_ratio=2.0)
    clean_points = sparse_model["points_xyz"][outlier_mask]
    print(f"Retained {clean_points.shape[0]}/{sparse_model['points_xyz'].shape[0]} points after outlier removal")

    geom = GeometryEstimate(
        poses=poses, points_xyz=clean_points, points_rgb=sparse_model["points_rgb"][outlier_mask],
        points_confidence=None, backend_name="colmap", is_metric_scale=False,
    )

    gps_fixes = []
    for pose in poses:
        name = Path(pose.frame_path).name
        f = frame_by_name.get(name)
        if f is not None and f.gps is not None:
            gps_fixes.append(GpsFix(name, f.gps.latitude, f.gps.longitude, f.gps.altitude_m))

    align_result = align_geometry_to_gps(geom, gps_fixes)
    print(f"Scale factor = {align_result.scale_factor:.4f}, mean GPS residual = {align_result.mean_alignment_residual_m:.3f} m")

    # Correct GT scoring: surveyed UTM32N -> WGS84 -> same ENU frame as align_result
    gt_by_name = {c.image_filename: c for c in gt_checkpoints}
    est_by_name = {Path(p.frame_path).name: p for p in align_result.aligned_poses}
    matched_est, matched_gt_enu, matched_names = [], [], []
    for name, gt in gt_by_name.items():
        pose = est_by_name.get(name)
        if pose is None:
            continue
        center = -pose.rotation.T @ pose.translation
        lon, lat, alt = UTM32N_TO_WGS84.transform(gt.utm_x, gt.utm_y, gt.utm_z)
        gt_enu = lla_to_enu(lat, lon, alt, align_result.origin_lat, align_result.origin_lon, align_result.origin_alt_m)
        matched_est.append(center)
        matched_gt_enu.append(gt_enu)
        matched_names.append(name)

    print(f"\nCheckpoints matched: {len(matched_est)}")
    report = {
        "scale_factor": float(align_result.scale_factor),
        "mean_gps_residual_m": float(align_result.mean_alignment_residual_m),
        "n_gt_checkpoints_matched": len(matched_est),
    }
    if matched_est:
        matched_est = np.array(matched_est)
        matched_gt_enu = np.array(matched_gt_enu)
        geo_metrics = compute_georeference_accuracy(matched_est, matched_gt_enu)
        print(f"Horizontal RMSE: {geo_metrics.horizontal_rmse_m:.3f} m")
        print(f"Vertical RMSE:   {geo_metrics.vertical_rmse_m:.3f} m")
        print(f"Max horizontal error: {geo_metrics.max_horizontal_error_m:.3f} m")
        per_point = [
            {"frame": matched_names[i], "est_enu": matched_est[i].tolist(), "gt_enu": matched_gt_enu[i].tolist(),
             "horizontal_error_m": float(np.linalg.norm(matched_est[i][:2] - matched_gt_enu[i][:2])),
             "vertical_error_m": float(abs(matched_est[i][2] - matched_gt_enu[i][2]))}
            for i in range(len(matched_names))
        ]
        for p in per_point:
            print(f"  {p['frame']}: horiz={p['horizontal_error_m']:.2f}m vert={p['vertical_error_m']:.2f}m")
        report["horizontal_rmse_m"] = geo_metrics.horizontal_rmse_m
        report["vertical_rmse_m"] = geo_metrics.vertical_rmse_m
        report["max_horizontal_error_m"] = geo_metrics.max_horizontal_error_m
        report["per_checkpoint"] = per_point

    (output_dir / "real_data_validation_report_corrected.json").write_text(json.dumps(report, indent=2))
    print(f"\n[Report] {output_dir / 'real_data_validation_report_corrected.json'}")


if __name__ == "__main__":
    main()
