"""
Phase 2 — COLMAP baseline pipeline: the safety-net, always-available geometry backend
(CLAUDE.md hard constraint #1 — COLMAP is the default path, never optional).

Wraps the COLMAP CLI (feature_extractor -> sequential_matcher -> mapper -> dense MVS ->
Poisson mesh) via subprocess, and parses COLMAP's documented text export format
(cameras.txt / images.txt / points3D.txt) directly — no pycolmap dependency, one fewer
prebuilt-wheel risk on Windows.

Sequential (not exhaustive) matching is used deliberately: PRD.md's input is a single
continuous flight trajectory, not unordered photo sets, so consecutive-frame matching
(with a small overlap window) is the geometrically correct and far cheaper choice.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from common.geometry_interface import CameraPose, GeometryEstimate  # noqa: E402


def find_colmap_binary() -> str:
    """Resolution order: COLMAP_BIN env var -> tools/ extracted release -> PATH."""
    env_path = os.environ.get("COLMAP_BIN")
    if env_path and Path(env_path).exists():
        return env_path

    tools_dir = REPO_ROOT / "tools"
    if tools_dir.exists():
        candidates = list(tools_dir.rglob("COLMAP.bat")) + list(tools_dir.rglob("colmap.exe"))
        if candidates:
            return str(candidates[0])

    found = shutil.which("colmap")
    if found:
        return found

    raise FileNotFoundError(
        "COLMAP binary not found. Set COLMAP_BIN env var, extract the release zip "
        "under tools/, or install COLMAP and add it to PATH."
    )


def _run(cmd: list[str], cwd: str | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({' '.join(cmd)}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _read_images_txt(path: Path) -> dict[int, dict]:
    """Parses COLMAP's images.txt (text model export format)."""
    images = {}
    lines = [l.strip() for l in path.read_text().splitlines() if l.strip() and not l.startswith("#")]
    for i in range(0, len(lines), 2):
        parts = lines[i].split()
        image_id = int(parts[0])
        qw, qx, qy, qz = map(float, parts[1:5])
        tx, ty, tz = map(float, parts[5:8])
        camera_id = int(parts[8])
        name = parts[9]

        # Line 2: POINTS2D[] as (X, Y, POINT3D_ID) triples, POINT3D_ID == -1 if unmatched.
        points2d_parts = lines[i + 1].split()
        points2d = []
        for j in range(0, len(points2d_parts), 3):
            x, y, point3d_id = float(points2d_parts[j]), float(points2d_parts[j + 1]), int(points2d_parts[j + 2])
            if point3d_id != -1:
                points2d.append((x, y, point3d_id))

        images[image_id] = {
            "quat_wxyz": (qw, qx, qy, qz),
            "translation": (tx, ty, tz),
            "camera_id": camera_id,
            "name": name,
            "points2d": points2d,  # [(x, y, point3D_id), ...] — 2D-3D correspondences
        }
    return images


def _read_cameras_txt(path: Path) -> dict[int, dict]:
    cameras = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        camera_id = int(parts[0])
        model, width, height = parts[1], int(parts[2]), int(parts[3])
        params = list(map(float, parts[4:]))
        cameras[camera_id] = {"model": model, "width": width, "height": height, "params": params}
    return cameras


def _read_points3d_txt(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[int, np.ndarray], list[int]]:
    """Returns (xyz, rgb, track_len, reprojection_error, id_to_xyz, point_ids).

    id_to_xyz is keyed by COLMAP's POINT3D_ID (not a dense array index), needed to
    resolve per-image 2D-3D correspondences for depth fusion (fuse_depth.py).
    reprojection_error is COLMAP's own mean track reprojection error per point (pixels)
    — a direct per-point confidence signal used by Phase 6's confidence module.
    point_ids is the POINT3D_ID for each row of xyz/rgb/track_len/reprojection_error, in
    the same order, so callers (e.g. class_tagging.py) can align rows back to tracks.
    """
    xyz, rgb, track_len, reproj_error, point_ids = [], [], [], [], []
    id_to_xyz: dict[int, np.ndarray] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        point3d_id = int(parts[0])
        point_xyz = list(map(float, parts[1:4]))
        xyz.append(point_xyz)
        rgb.append(list(map(int, parts[4:7])))
        reproj_error.append(float(parts[7]))
        n_track_elems = (len(parts) - 8) // 2
        track_len.append(n_track_elems)
        id_to_xyz[point3d_id] = np.array(point_xyz)
        point_ids.append(point3d_id)
    if not xyz:
        return (np.zeros((0, 3)), np.zeros((0, 3), dtype=np.uint8), np.zeros((0,)),
                np.zeros((0,)), {}, [])
    return (
        np.array(xyz), np.array(rgb, dtype=np.uint8), np.array(track_len, dtype=np.float32),
        np.array(reproj_error, dtype=np.float32), id_to_xyz, point_ids,
    )


def _quat_to_rotmat(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
    n = np.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    qw, qx, qy, qz = qw / n, qx / n, qy / n, qz / n
    return np.array([
        [1 - 2 * (qy**2 + qz**2), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
        [2 * (qx * qy + qz * qw), 1 - 2 * (qx**2 + qz**2), 2 * (qy * qz - qx * qw)],
        [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx**2 + qy**2)],
    ])


def _camera_intrinsics(camera: dict) -> np.ndarray:
    model, params = camera["model"], camera["params"]
    if model in ("SIMPLE_PINHOLE", "SIMPLE_RADIAL", "SIMPLE_RADIAL_FISHEYE"):
        f, cx, cy = params[0], params[1], params[2]
        fx = fy = f
    elif model in ("PINHOLE", "OPENCV", "FULL_OPENCV", "RADIAL"):
        fx, fy, cx, cy = params[0], params[1], params[2], params[3]
    else:
        fx = fy = params[0]
        cx, cy = params[1] if len(params) > 1 else 0.0, params[2] if len(params) > 2 else 0.0
    return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])


def read_sparse_text_model(sparse_txt_dir: str | Path) -> dict:
    """Public reader for a COLMAP text-format sparse model — shared by ColmapBackend
    and downstream stages (e.g. depth_fusion/fuse_depth.py) that need 2D-3D
    correspondences, not just the final GeometryEstimate."""
    sparse_txt_dir = Path(sparse_txt_dir)
    images = _read_images_txt(sparse_txt_dir / "images.txt")
    cameras = _read_cameras_txt(sparse_txt_dir / "cameras.txt")
    points_xyz, points_rgb, track_len, reproj_error, id_to_xyz, point_ids = _read_points3d_txt(
        sparse_txt_dir / "points3D.txt"
    )
    return {
        "images": images,
        "cameras": cameras,
        "points_xyz": points_xyz,
        "points_rgb": points_rgb,
        "track_len": track_len,
        "reprojection_error": reproj_error,
        "point3d_id_to_xyz": id_to_xyz,
        "point_ids": point_ids,
    }


class ColmapBackend:
    name = "colmap"

    def __init__(self, colmap_bin: str | None = None, use_gpu: bool = True):
        self.colmap_bin = colmap_bin or find_colmap_binary()
        self.use_gpu = use_gpu

    def run_sparse_reconstruction(
        self, image_dir: str | Path, work_dir: str | Path, mask_dir: str | Path | None = None
    ) -> Path:
        """feature_extractor -> sequential_matcher -> mapper -> export as text.
        Returns the path to the exported text sparse model directory.

        mask_dir: optional per-image mask directory (ARCHITECTURE.md: dynamic classes
        masked out before reconstruction). Each mask is `<image_filename>.png`, same
        pixel dimensions as the image, 0 = ignore pixel for feature extraction,
        255 = use it. See `src/frame_processing/masking.py` for how these are built
        from segmentation output.
        """
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        db_path = work_dir / "database.db"
        sparse_dir = work_dir / "sparse"
        sparse_dir.mkdir(exist_ok=True)
        sparse_txt_dir = work_dir / "sparse_txt"
        sparse_txt_dir.mkdir(exist_ok=True)

        gpu_flag = "1" if self.use_gpu else "0"

        feature_extractor_cmd = [
            self.colmap_bin, "feature_extractor",
            "--database_path", str(db_path),
            "--image_path", str(image_dir),
            "--ImageReader.camera_model", "SIMPLE_RADIAL",
            "--ImageReader.single_camera", "1",
            "--FeatureExtraction.use_gpu", gpu_flag,
        ]
        if mask_dir is not None:
            feature_extractor_cmd += ["--ImageReader.mask_path", str(mask_dir)]
        _run(feature_extractor_cmd)

        _run([
            self.colmap_bin, "sequential_matcher",
            "--database_path", str(db_path),
            "--FeatureMatching.use_gpu", gpu_flag,
            "--SequentialMatching.overlap", "10",
        ])

        _run([
            self.colmap_bin, "mapper",
            "--database_path", str(db_path),
            "--image_path", str(image_dir),
            "--output_path", str(sparse_dir),
        ])

        model_0 = sparse_dir / "0"
        if not model_0.exists():
            raise RuntimeError(
                f"COLMAP mapper produced no reconstruction at {model_0} — "
                "check frame overlap/quality; sparse SfM may have failed to register enough images."
            )
        # NOTE: if frame overlap/quality is poor, `mapper` can produce multiple
        # disconnected components (sparse/0, sparse/1, ...). We only use component 0
        # (the largest, by COLMAP's own convention) — a genuinely fragmented flight
        # path would need per-component handling this MVP doesn't do yet.

        _run([
            self.colmap_bin, "model_converter",
            "--input_path", str(model_0),
            "--output_path", str(sparse_txt_dir),
            "--output_type", "TXT",
        ])
        return sparse_txt_dir

    def run_dense_reconstruction(
        self, image_dir: str | Path, sparse_model_dir: str | Path, work_dir: str | Path
    ) -> Path:
        """image_undistorter -> patch_match_stereo (needs CUDA) -> stereo_fusion ->
        poisson_mesher. Returns the path to the meshed .ply."""
        work_dir = Path(work_dir)
        dense_dir = work_dir / "dense"
        dense_dir.mkdir(parents=True, exist_ok=True)

        _run([
            self.colmap_bin, "image_undistorter",
            "--image_path", str(image_dir),
            "--input_path", str(sparse_model_dir),
            "--output_path", str(dense_dir),
            "--output_type", "COLMAP",
        ])

        _run([
            self.colmap_bin, "patch_match_stereo",
            "--workspace_path", str(dense_dir),
            "--workspace_format", "COLMAP",
        ])

        fused_ply = dense_dir / "fused.ply"
        _run([
            self.colmap_bin, "stereo_fusion",
            "--workspace_path", str(dense_dir),
            "--workspace_format", "COLMAP",
            "--output_path", str(fused_ply),
        ])

        mesh_ply = dense_dir / "meshed-poisson.ply"
        _run([
            self.colmap_bin, "poisson_mesher",
            "--input_path", str(fused_ply),
            "--output_path", str(mesh_ply),
        ])
        return mesh_ply

    def estimate_geometry(
        self, frame_paths: list[str], work_dir: str | Path, mask_dir: str | Path | None = None
    ) -> GeometryEstimate:
        """Satisfies the GeometryBackend protocol: sparse reconstruction only (fast
        path). Dense MVS/meshing is a separate call (`run_dense_reconstruction`) since
        it's much more expensive and not every caller needs it."""
        work_dir = Path(work_dir)
        image_dirs = {str(Path(p).parent) for p in frame_paths}
        if len(image_dirs) != 1:
            raise ValueError(
                "COLMAP needs all frames in a single directory; got frames from "
                f"{len(image_dirs)} different directories."
            )
        image_dir = image_dirs.pop()

        sparse_txt_dir = self.run_sparse_reconstruction(image_dir, work_dir, mask_dir=mask_dir)
        model = read_sparse_text_model(sparse_txt_dir)

        poses = []
        for image_id, img in model["images"].items():
            camera = model["cameras"][img["camera_id"]]
            r = _quat_to_rotmat(*img["quat_wxyz"])
            t = np.array(img["translation"])
            k = _camera_intrinsics(camera)
            poses.append(CameraPose(frame_path=img["name"], rotation=r, translation=t, intrinsics=k))

        return GeometryEstimate(
            poses=poses,
            points_xyz=model["points_xyz"],
            points_rgb=model["points_rgb"],
            points_confidence=model["track_len"],  # track length = # frames observing the point
            backend_name=self.name,
            is_metric_scale=False,
        )
