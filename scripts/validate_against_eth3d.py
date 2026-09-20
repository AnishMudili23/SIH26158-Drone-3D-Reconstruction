"""
Continuous-improvement Cycle 1: validate reconstruction accuracy against ETH3D's real,
laser-scan-calibrated ground truth — closing PRD.md Section 5's stated validation
target ("validated against ETH3D ground truth") which had not actually been done yet
(everything up to this point was validated against our own synthetic scene, honestly
flagged throughout PROGRESS.md as the one remaining gap).

Method: run our real ColmapBackend against ETH3D's real "delivery_area" scene images,
then align our reconstruction's camera centers to ETH3D's own ground-truth camera
poses (dslr_calibration_undistorted/images.txt — independently calibrated against
their laser scan, i.e. genuinely metric) using the same Umeyama similarity alignment
already validated in Phase 3. The post-alignment residual, in real millimeters, is a
direct, independent measure of our COLMAP pipeline's reconstruction accuracy — not
self-consistency against our own synthetic data.
"""
import sys
sys.path.insert(0, "src")
import numpy as np
from pathlib import Path

from reconstruction.colmap_backend import (
    ColmapBackend, _quat_to_rotmat, _read_images_txt, _read_cameras_txt,
)
from common.alignment import umeyama_alignment


def read_eth3d_camera_calibration(cameras_txt_path: str) -> tuple[str, str]:
    """Extract (camera_model, camera_params_csv) from cameras.txt."""
    cameras = _read_cameras_txt(Path(cameras_txt_path))
    if not cameras:
        raise ValueError(f"No camera found in {cameras_txt_path}")
    cam = list(cameras.values())[0]
    model = cam["model"]
    params_csv = ",".join(str(p) for p in cam["params"])
    return model, params_csv


def read_eth3d_gt_poses(images_txt_path: str) -> dict[str, np.ndarray]:
    """ETH3D's dslr_calibration_undistorted/images.txt is COLMAP's own text format —
    reuse our existing parser, extract camera centers (C = -R^T @ t)."""
    images = _read_images_txt(Path(images_txt_path))
    centers = {}
    for image_id, img in images.items():
        r = _quat_to_rotmat(*img["quat_wxyz"])
        t = np.array(img["translation"])
        centers[Path(img["name"]).name] = -r.T @ t
    return centers


def main(scene_dir: str, work_dir: str, max_images: int | None = None):
    scene_dir = Path(scene_dir)
    image_dir = scene_dir / "images" / "dslr_images_undistorted"
    gt_images_txt = scene_dir / "dslr_calibration_undistorted" / "images.txt"
    gt_cameras_txt = scene_dir / "dslr_calibration_undistorted" / "cameras.txt"

    if not image_dir.exists():
        raise FileNotFoundError(f"{image_dir} not found — check extraction")
    if not gt_images_txt.exists():
        raise FileNotFoundError(f"{gt_images_txt} not found — check extraction")

    gt_centers = read_eth3d_gt_poses(str(gt_images_txt))
    print(f"Ground truth: {len(gt_centers)} camera poses")

    frame_paths = sorted({str(p) for p in image_dir.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png"]})
    if max_images:
        # Evenly sample rather than truncate, to keep spatial coverage of the scene.
        idx = np.linspace(0, len(frame_paths) - 1, max_images).astype(int)
        frame_paths = [frame_paths[i] for i in sorted(set(idx))]
    print(f"Running COLMAP on {len(frame_paths)} real ETH3D images...")

    cam_model = "SIMPLE_RADIAL"
    cam_params = None
    if gt_cameras_txt.exists():
        cam_model, cam_params = read_eth3d_camera_calibration(str(gt_cameras_txt))
        print(f"Using known calibration: model={cam_model}, params={cam_params}")

    backend = ColmapBackend(camera_model=cam_model, camera_params=cam_params)
    geometry = backend.estimate_geometry(frame_paths, work_dir)
    print(f"COLMAP registered {len(geometry.poses)} / {len(frame_paths)} frames, "
          f"{geometry.points_xyz.shape[0]} sparse points")

    matched_our_centers = []
    matched_gt_centers = []
    for pose in geometry.poses:
        name = Path(pose.frame_path).name
        if name in gt_centers:
            our_center = -pose.rotation.T @ pose.translation
            matched_our_centers.append(our_center)
            matched_gt_centers.append(gt_centers[name])

    print(f"Matched {len(matched_our_centers)} frames against ground truth")
    if len(matched_our_centers) < 3:
        print("Too few matches for alignment — reconstruction likely failed to register enough frames.")
        return

    our_arr = np.array(matched_our_centers)
    gt_arr = np.array(matched_gt_centers)

    scale, rotation, translation = umeyama_alignment(our_arr, gt_arr)
    aligned = (scale * rotation @ our_arr.T).T + translation
    residuals_m = np.linalg.norm(aligned - gt_arr, axis=1)

    print(f"\n=== ETH3D delivery_area real-ground-truth validation ===")
    print(f"Recovered scale factor: {scale:.4f}")
    print(f"Camera-position residual after alignment (meters):")
    print(f"  mean = {residuals_m.mean()*1000:.1f} mm")
    print(f"  median = {np.median(residuals_m)*1000:.1f} mm")
    print(f"  max = {residuals_m.max()*1000:.1f} mm")
    print(f"  std = {residuals_m.std()*1000:.1f} mm")

    scene_scale_m = np.linalg.norm(gt_arr.max(axis=0) - gt_arr.min(axis=0))
    print(f"Scene extent (diagonal): {scene_scale_m:.2f} m")
    print(f"Relative error: {residuals_m.mean() / scene_scale_m * 100:.3f}%")


if __name__ == "__main__":
    scene = sys.argv[1] if len(sys.argv) > 1 else "data/datasets/eth3d/delivery_area"
    work = sys.argv[2] if len(sys.argv) > 2 else "outputs/eth3d_validation"
    max_imgs = int(sys.argv[3]) if len(sys.argv) > 3 else None
    main(scene, work, max_imgs)
