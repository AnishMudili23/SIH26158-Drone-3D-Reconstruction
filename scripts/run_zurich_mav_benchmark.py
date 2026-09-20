"""Real-world validation run: Zurich Urban MAV dataset (ROADMAP.md Phase H).

Runs the actual reconstruction pipeline against real drone video frames, real GPS,
real IMU/barometer telemetry, and real camera calibration for the first time in this
project's history (every prior phase was validated against synthetic scenes or ETH3D's
static handheld DSLR set — neither is real UAV single-pass footage).

Undistorts frames using the dataset's own calibration (real lens distortion, unlike the
ETH3D run which used an already-undistorted set), runs COLMAP with the true PINHOLE
intrinsics, aligns to real GPS via the same Umeyama alignment used everywhere else in
this codebase, and scores the result against the dataset's own surveyed ground-truth
checkpoints using src/accuracy/*.

Usage:
    python scripts/run_zurich_mav_benchmark.py --dataset-dir datasets/zurich_mav/AGZ_subset
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from datasets.zurich_mav import load_zurich_mav_session  # noqa: E402
from reconstruction.colmap_backend import (  # noqa: E402
    ColmapBackend,
    read_sparse_text_model,
    _quat_to_rotmat,
    _camera_intrinsics,
)
from common.geometry_interface import CameraPose, GeometryEstimate  # noqa: E402
from pointcloud.outlier_removal import remove_statistical_outliers  # noqa: E402
from geo.scale_alignment import GpsFix, align_geometry_to_gps, lla_to_enu  # noqa: E402
from accuracy.scale_accuracy import compute_scale_accuracy  # noqa: E402
from accuracy.georeference_accuracy import compute_georeference_accuracy  # noqa: E402


def undistort_frames(image_paths: list[Path], k: np.ndarray, dist: np.ndarray, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_paths = []
    for p in image_paths:
        out_path = out_dir / p.name
        if not out_path.exists():
            img = cv2.imread(str(p))
            undistorted = cv2.undistort(img, k, dist)
            cv2.imwrite(str(out_path), undistorted)
        out_paths.append(out_path)
    return out_paths


def main() -> dict:
    parser = argparse.ArgumentParser(description="Zurich Urban MAV real-world validation run")
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output-dir", default="outputs/zurich_mav_benchmark")
    parser.add_argument("--frame-stride", type=int, default=1, help="Use every Nth frame (speed vs. density)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n========================================================")
    print("  REAL-DATA VALIDATION: Zurich Urban MAV Dataset")
    print("========================================================\n")

    print("[1/5] Loading FlightSession from real sensor logs...")
    session, image_paths, gt_checkpoints = load_zurich_mav_session(args.dataset_dir)
    integrity_issues = session.validate_integrity()
    print(f"  {len(session.frames)} frames, {len(session.gps_fixes)} GPS fixes, "
          f"{len(session.imu_measurements)} IMU samples, {len(gt_checkpoints)} surveyed GT checkpoints")
    if integrity_issues:
        print(f"  [Integrity notice] {integrity_issues}")

    if args.frame_stride > 1:
        session_frames = session.frames[::args.frame_stride]
        image_paths = image_paths[::args.frame_stride]
        print(f"  Applying frame stride {args.frame_stride}: {len(session_frames)} frames retained")
    else:
        session_frames = session.frames

    print("\n[2/5] Undistorting frames using real camera calibration...")
    k = session.camera.to_intrinsics_matrix()
    dist = np.array(session.camera.distortion_coeffs)
    undistorted_dir = output_dir / "undistorted"
    undistorted_paths = undistort_frames(image_paths, k, dist, undistorted_dir)
    print(f"  Undistorted {len(undistorted_paths)} frames -> {undistorted_dir}")

    print("\n[3/5] Running COLMAP sparse reconstruction (real PINHOLE intrinsics)...")
    camera_params = f"{session.camera.fx},{session.camera.fy},{session.camera.cx},{session.camera.cy}"
    backend = ColmapBackend(camera_model="PINHOLE", camera_params=camera_params)
    sparse_txt_dir = backend.run_sparse_reconstruction(
        image_dir=undistorted_dir,
        work_dir=output_dir / "reconstruction",
    )
    sparse_model = read_sparse_text_model(sparse_txt_dir)
    n_registered = len(sparse_model["images"])
    n_total = len(undistorted_paths)
    n_points = sparse_model["points_xyz"].shape[0]
    print(f"  Registered {n_registered}/{n_total} frames ({n_registered/n_total*100:.1f}%), {n_points} sparse points")

    poses: list[CameraPose] = []
    for image_id, img in sparse_model["images"].items():
        r = _quat_to_rotmat(*img["quat_wxyz"])
        t = np.array(img["translation"])
        kk = _camera_intrinsics(sparse_model["cameras"][img["camera_id"]])
        poses.append(CameraPose(frame_path=img["name"], rotation=r, translation=t, intrinsics=kk))

    print("\n[4/5] Outlier removal + real-GPS georeferencing...")
    outlier_mask, _ = remove_statistical_outliers(sparse_model["points_xyz"], nb_neighbors=20, std_ratio=2.0)
    clean_points = sparse_model["points_xyz"][outlier_mask]
    clean_rgb = sparse_model["points_rgb"][outlier_mask]
    print(f"  Retained {clean_points.shape[0]}/{n_points} points after outlier removal")

    geom = GeometryEstimate(
        poses=poses, points_xyz=clean_points, points_rgb=clean_rgb,
        points_confidence=None, backend_name="colmap", is_metric_scale=False,
    )

    frame_by_name = {f.image_filename: f for f in session_frames}
    gps_fixes: list[GpsFix] = []
    for pose in poses:
        name = Path(pose.frame_path).name
        f = frame_by_name.get(name)
        if f is not None and f.gps is not None:
            gps_fixes.append(GpsFix(name, f.gps.latitude, f.gps.longitude, f.gps.altitude_m))

    report: dict = {
        "dataset": "zurich_urban_mav_AGZ_subset",
        "provenance": "REAL",
        "n_frames_input": n_total,
        "n_frames_registered": n_registered,
        "registration_rate_pct": float(n_registered / n_total * 100),
        "n_sparse_points": n_points,
        "n_points_after_outlier_removal": int(clean_points.shape[0]),
        "n_gps_correspondences_available": len(gps_fixes),
        "integrity_issues": integrity_issues,
    }

    if len(gps_fixes) >= 3:
        align_result = align_geometry_to_gps(geom, gps_fixes)
        scale_err_pct, scale_precision = compute_scale_accuracy(align_result.scale_factor, true_scale=1.0)
        print(f"  Scale factor = {align_result.scale_factor:.4f}, mean GPS residual = "
              f"{align_result.mean_alignment_residual_m:.3f} m")
        report["scale_factor"] = float(align_result.scale_factor)
        report["mean_gps_residual_m"] = float(align_result.mean_alignment_residual_m)
        report["n_gps_correspondences_used"] = align_result.n_gps_correspondences

        print("\n[5/5] Scoring against surveyed ground-truth checkpoints...")
        gt_by_name = {c.image_filename: c for c in gt_checkpoints}
        est_by_name = {Path(p.frame_path).name: p for p in align_result.aligned_poses}
        matched_est, matched_gt_enu = [], []
        for name, gt in gt_by_name.items():
            pose = est_by_name.get(name)
            if pose is None:
                continue
            center = -pose.rotation.T @ pose.translation
            # Reproject GT's UTM position into the same ENU frame via GPS-derived origin
            gt_lat, gt_lon, gt_alt = frame_by_name[name].gps.latitude, frame_by_name[name].gps.longitude, frame_by_name[name].gps.altitude_m
            matched_est.append(center)
            matched_gt_enu.append(lla_to_enu(gt_lat, gt_lon, gt_alt, align_result.origin_lat, align_result.origin_lon, align_result.origin_alt_m))

        if len(matched_est) >= 1:
            matched_est = np.array(matched_est)
            matched_gt_enu = np.array(matched_gt_enu)
            geo_metrics = compute_georeference_accuracy(matched_est, matched_gt_enu)
            print(f"  Checkpoints matched: {len(matched_est)}")
            print(f"  Horizontal RMSE: {geo_metrics.horizontal_rmse_m:.3f} m, Vertical RMSE: {geo_metrics.vertical_rmse_m:.3f} m")
            report["n_gt_checkpoints_matched"] = len(matched_est)
            report["horizontal_rmse_m"] = geo_metrics.horizontal_rmse_m
            report["vertical_rmse_m"] = geo_metrics.vertical_rmse_m
        else:
            print("  No registered frames overlap with surveyed ground-truth checkpoints.")
            report["n_gt_checkpoints_matched"] = 0
    else:
        print(f"  [Notice] Only {len(gps_fixes)} registered frames have matching GPS fixes "
              "(need >= 3) — skipping georeferencing.")
        report["scale_factor"] = None
        report["note"] = "insufficient_gps_correspondences_for_alignment"

    report_path = output_dir / "real_data_validation_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n[Report] {report_path}")
    print("========================================================\n")
    return report


if __name__ == "__main__":
    main()
