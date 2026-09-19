"""
Phase 2 — COLMAP Baseline Pipeline orchestrator.

Ties Phase 1 output (quality-filtered, class-masked keyframes) into COLMAP's full
sparse -> dense -> mesh pipeline.

Definition of done (ROADMAP.md): a real .ply/.obj output from a real test video,
viewable in any generic 3D viewer (e.g. MeshLab) as a sanity check.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from frame_processing.masking import build_colmap_masks  # noqa: E402
from reconstruction.colmap_backend import ColmapBackend  # noqa: E402


def run_phase2(
    kept_frames_dir: str,
    masks_dir: str | None,
    work_dir: str,
    run_dense: bool = True,
) -> dict:
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = sorted(str(p) for p in Path(kept_frames_dir).glob("*.jpg"))
    if not frame_paths:
        raise ValueError(f"No .jpg frames found in {kept_frames_dir}")

    colmap_mask_dir = None
    if masks_dir is not None and Path(masks_dir).exists():
        class_mask_paths = []
        matched_frame_paths = []
        for fp in frame_paths:
            candidate = Path(masks_dir) / (Path(fp).stem + "_mask.png")
            if candidate.exists():
                class_mask_paths.append(str(candidate))
                matched_frame_paths.append(fp)
        if class_mask_paths:
            colmap_mask_dir = work_dir / "colmap_masks"
            build_colmap_masks(matched_frame_paths, class_mask_paths, colmap_mask_dir)

    backend = ColmapBackend()
    sparse_work_dir = work_dir / "sparse_recon"
    geometry = backend.estimate_geometry(frame_paths, sparse_work_dir, mask_dir=colmap_mask_dir)

    result = {
        "n_frames_input": len(frame_paths),
        "n_poses_registered": len(geometry.poses),
        "n_sparse_points": int(geometry.points_xyz.shape[0]),
        "used_dynamic_object_masks": colmap_mask_dir is not None,
        "mesh_path": None,
    }

    if run_dense:
        sparse_binary_model = sparse_work_dir / "sparse" / "0"
        mesh_path = backend.run_dense_reconstruction(
            image_dir=kept_frames_dir,
            sparse_model_dir=sparse_binary_model,
            work_dir=work_dir / "dense_recon",
        )
        result["mesh_path"] = str(mesh_path)

    (work_dir / "phase2_result.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_phase2.py <kept_frames_dir> <work_dir> [masks_dir]")
        sys.exit(1)
    masks_dir = sys.argv[3] if len(sys.argv) > 3 else None
    result = run_phase2(sys.argv[1], sys.argv[2], masks_dir)
    print(json.dumps(result, indent=2))
