"""
Phase 1 — Frame extraction from a raw drone video at a controlled interval.

Per CLAUDE.md hard constraint #4: this is always the *first* stage — we never hand
every raw frame to later stages. Extraction interval is time-based (fps target), not
"every frame," so a 4K/60fps video doesn't dump thousands of near-identical frames
into the quality filter.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2


@dataclass
class ExtractedFrame:
    frame_index: int          # index in the original video
    timestamp_s: float        # seconds into the video
    path: str                 # where it was written


@dataclass
class ExtractionReport:
    source_video: str
    source_fps: float
    source_frame_count: int
    source_duration_s: float
    target_extract_fps: float
    n_frames_extracted: int
    output_dir: str


def extract_frames(
    video_path: str | Path,
    output_dir: str | Path,
    target_extract_fps: float = 2.0,
    jpeg_quality: int = 95,
) -> tuple[ExtractionReport, list[ExtractedFrame]]:
    """Extract frames at `target_extract_fps`, regardless of the source frame rate.

    Rationale (ARCHITECTURE.md): drone video is typically 24-60fps but adjacent frames
    at that rate carry almost no new parallax over a few meters of flight — 1-3fps is
    the standard photogrammetry extraction rate. This is step 1 of Phase 1's filtering,
    before blur/duplicate/coverage filtering even runs.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Could not open video: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    source_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    source_duration_s = source_frame_count / source_fps if source_fps > 0 else 0.0

    frame_interval = max(1, round(source_fps / target_extract_fps))

    extracted: list[ExtractedFrame] = []
    frame_idx = 0
    saved_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % frame_interval == 0:
            timestamp_s = frame_idx / source_fps if source_fps > 0 else 0.0
            out_path = output_dir / f"frame_{saved_idx:06d}.jpg"
            cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
            extracted.append(ExtractedFrame(frame_idx, timestamp_s, str(out_path)))
            saved_idx += 1
        frame_idx += 1
    cap.release()

    report = ExtractionReport(
        source_video=str(video_path),
        source_fps=source_fps,
        source_frame_count=source_frame_count,
        source_duration_s=source_duration_s,
        target_extract_fps=target_extract_fps,
        n_frames_extracted=len(extracted),
        output_dir=str(output_dir),
    )
    return report, extracted


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python extract_frames.py <video_path> <output_dir> [target_fps]")
        sys.exit(1)
    fps = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    report, frames = extract_frames(sys.argv[1], sys.argv[2], fps)
    print(json.dumps(asdict(report), indent=2))
