"""
Phase 1 — Frame quality filtering: blur detection, near-duplicate detection, and
flight-path coverage check.

Per ARCHITECTURE.md's Frame Quality Filter stage. Each check is independent and
composable so Phase 1's pipeline can log *why* a frame was dropped, not just that it was.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image


def laplacian_variance(image_bgr: np.ndarray) -> float:
    """Higher = sharper. Standard blur-detection metric (variance of the Laplacian)."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def perceptual_hash(image_bgr: np.ndarray) -> imagehash.ImageHash:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return imagehash.phash(Image.fromarray(rgb))


@dataclass
class FrameQualityRecord:
    path: str
    frame_index: int
    blur_score: float
    is_blurry: bool
    is_near_duplicate: bool
    duplicate_of: str | None
    kept: bool
    drop_reason: str | None


@dataclass
class QualityFilterReport:
    n_input_frames: int
    n_kept: int
    n_dropped_blur: int
    n_dropped_duplicate: int
    blur_threshold: float
    hash_distance_threshold: int


def filter_frames(
    frame_paths: list[str],
    blur_threshold: float = 100.0,
    hash_distance_threshold: int = 5,
    frame_indices: list[int] | None = None,
) -> tuple[QualityFilterReport, list[FrameQualityRecord]]:
    """Blur + near-duplicate filtering, in that order (cheap check first).

    blur_threshold: Laplacian variance below this = "blurry" (classic OpenCV default
    ballpark is 100 for general photography; drone footage with motion blur/compression
    tends to sit lower, so this is a starting point to tune against real footage).
    hash_distance_threshold: perceptual-hash Hamming distance below this = "near duplicate"
    of a frame we already kept (imagehash's phash is 64-bit; <=5 is a common "very similar"
    cutoff).
    frame_indices: original-video frame indices matching `frame_paths` (as produced by
    extraction), used so downstream coverage checking can look up timestamps. Defaults
    to the list position if not given.
    """
    if frame_indices is None:
        frame_indices = list(range(len(frame_paths)))
    records: list[FrameQualityRecord] = []
    kept_hashes: list[tuple[imagehash.ImageHash, str]] = []
    n_dropped_blur = 0
    n_dropped_duplicate = 0

    for idx, path in enumerate(frame_paths):
        img = cv2.imread(path)
        if img is None:
            records.append(FrameQualityRecord(
                path=path, frame_index=frame_indices[idx], blur_score=0.0, is_blurry=True,
                is_near_duplicate=False, duplicate_of=None, kept=False,
                drop_reason="unreadable_file",
            ))
            continue

        blur_score = laplacian_variance(img)
        is_blurry = blur_score < blur_threshold
        if is_blurry:
            n_dropped_blur += 1
            records.append(FrameQualityRecord(
                path=path, frame_index=frame_indices[idx], blur_score=blur_score, is_blurry=True,
                is_near_duplicate=False, duplicate_of=None, kept=False,
                drop_reason="blurry",
            ))
            continue

        phash = perceptual_hash(img)
        duplicate_of = None
        for kept_hash, kept_path in kept_hashes:
            if (phash - kept_hash) <= hash_distance_threshold:
                duplicate_of = kept_path
                break

        if duplicate_of is not None:
            n_dropped_duplicate += 1
            records.append(FrameQualityRecord(
                path=path, frame_index=frame_indices[idx], blur_score=blur_score, is_blurry=False,
                is_near_duplicate=True, duplicate_of=duplicate_of, kept=False,
                drop_reason="near_duplicate",
            ))
            continue

        kept_hashes.append((phash, path))
        records.append(FrameQualityRecord(
            path=path, frame_index=frame_indices[idx], blur_score=blur_score, is_blurry=False,
            is_near_duplicate=False, duplicate_of=None, kept=True, drop_reason=None,
        ))

    report = QualityFilterReport(
        n_input_frames=len(frame_paths),
        n_kept=sum(1 for r in records if r.kept),
        n_dropped_blur=n_dropped_blur,
        n_dropped_duplicate=n_dropped_duplicate,
        blur_threshold=blur_threshold,
        hash_distance_threshold=hash_distance_threshold,
    )
    return report, records


@dataclass
class CoverageCheckResult:
    n_kept_frames: int
    max_gap_frames: int
    max_gap_timestamps_s: tuple[float, float] | None
    coverage_warning: str | None


def check_flight_path_coverage(
    kept_records: list[FrameQualityRecord],
    frame_timestamps_s: dict[int, float],
    max_acceptable_gap_s: float = 5.0,
) -> CoverageCheckResult:
    """Make sure filtering didn't carve a hole out of the flight path.

    Aggressive blur/duplicate filtering can accidentally drop an entire *contiguous*
    stretch of the flight (e.g. a real motion-blur patch during a sharp turn), leaving a
    gap in trajectory coverage that later stages can't reconstruct across. This flags
    that case rather than silently proceeding with a broken sequence.
    """
    kept_indices = sorted(r.frame_index for r in kept_records if r.kept)
    if len(kept_indices) < 2:
        return CoverageCheckResult(
            n_kept_frames=len(kept_indices), max_gap_frames=0,
            max_gap_timestamps_s=None,
            coverage_warning="fewer than 2 frames kept — cannot assess coverage",
        )

    max_gap = 0
    max_gap_pair = (kept_indices[0], kept_indices[0])
    for a, b in zip(kept_indices, kept_indices[1:]):
        gap = b - a
        if gap > max_gap:
            max_gap = gap
            max_gap_pair = (a, b)

    t_a = frame_timestamps_s.get(max_gap_pair[0])
    t_b = frame_timestamps_s.get(max_gap_pair[1])
    gap_s = (t_b - t_a) if (t_a is not None and t_b is not None) else None

    warning = None
    if gap_s is not None and gap_s > max_acceptable_gap_s:
        warning = (
            f"Largest gap between consecutive kept frames is {gap_s:.1f}s "
            f"(frames {max_gap_pair[0]}->{max_gap_pair[1]}), exceeding the "
            f"{max_acceptable_gap_s}s threshold. This section of the flight path may "
            f"be under-covered for SfM."
        )

    return CoverageCheckResult(
        n_kept_frames=len(kept_indices),
        max_gap_frames=max_gap,
        max_gap_timestamps_s=(t_a, t_b) if gap_s is not None else None,
        coverage_warning=warning,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python quality_filter.py <frames_dir>")
        sys.exit(1)
    frames_dir = Path(sys.argv[1])
    paths = sorted(str(p) for p in frames_dir.glob("*.jpg"))
    report, records = filter_frames(paths)
    print(json.dumps(asdict(report), indent=2))
