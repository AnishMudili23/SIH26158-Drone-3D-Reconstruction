"""
Phase 1 — full pipeline: video -> extracted frames -> quality-filtered frames ->
coverage check -> per-frame semantic segmentation masks.

Definition of done (ROADMAP.md): feed in a video clip, get out a filtered frame folder
with a visible before/after count, plus a per-frame segmentation mask for each retained
frame.
"""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from frame_processing.extract_frames import extract_frames  # noqa: E402
from frame_processing.quality_filter import (  # noqa: E402
    check_flight_path_coverage,
    filter_frames,
)


def run_phase1(
    video_path: str,
    work_dir: str,
    target_extract_fps: float = 2.0,
    blur_threshold: float = 100.0,
    hash_distance_threshold: int = 5,
    run_segmentation: bool = True,
) -> dict:
    work_dir = Path(work_dir)
    raw_frames_dir = work_dir / "raw_frames"
    kept_frames_dir = work_dir / "kept_frames"
    masks_dir = work_dir / "masks"
    for d in (raw_frames_dir, kept_frames_dir, masks_dir):
        d.mkdir(parents=True, exist_ok=True)

    extraction_report, extracted = extract_frames(video_path, raw_frames_dir, target_extract_fps)
    frame_timestamps = {f.frame_index: f.timestamp_s for f in extracted}

    all_paths = [f.path for f in extracted]
    all_indices = [f.frame_index for f in extracted]
    filter_report, filter_records = filter_frames(
        all_paths, blur_threshold, hash_distance_threshold, frame_indices=all_indices
    )

    kept_records = [r for r in filter_records if r.kept]
    for r in kept_records:
        shutil.copy(r.path, kept_frames_dir / Path(r.path).name)

    coverage_result = check_flight_path_coverage(filter_records, frame_timestamps)

    result = {
        "video_path": video_path,
        "extraction": asdict(extraction_report),
        "quality_filter": asdict(filter_report),
        "coverage": asdict(coverage_result),
        "before_after_summary": (
            f"{extraction_report.n_frames_extracted} extracted -> "
            f"{filter_report.n_kept} kept "
            f"({filter_report.n_dropped_blur} dropped blur, "
            f"{filter_report.n_dropped_duplicate} dropped duplicate)"
        ),
        "kept_frames_dir": str(kept_frames_dir),
    }

    if run_segmentation:
        try:
            from frame_processing.segmentation import segment_keyframes

            kept_paths = sorted(str(p) for p in kept_frames_dir.glob("*.jpg"))
            seg_records = segment_keyframes(kept_paths, masks_dir)
            result["segmentation"] = {
                "n_masks_written": len(seg_records),
                "masks_dir": str(masks_dir),
            }
        except ImportError as e:
            result["segmentation"] = {"skipped_reason": f"dependency not available: {e}"}

    (work_dir / "phase1_manifest.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_phase1.py <video_path> <work_dir> [target_fps]")
        sys.exit(1)
    fps = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    result = run_phase1(sys.argv[1], sys.argv[2], target_extract_fps=fps)
    print(json.dumps(result, indent=2))
