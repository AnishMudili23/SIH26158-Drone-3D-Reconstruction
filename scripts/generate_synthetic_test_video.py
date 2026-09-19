"""
Generates a small synthetic test video to validate the Phase 1 pipeline mechanics
(extraction interval, blur detection, near-duplicate detection) without needing the
real UAVid dataset downloaded yet (UAVid requires manual registration at uavid.nl —
see PROGRESS.md Phase 1 entry for status).

Not a substitute for real drone footage validation — this only proves the *code* is
correct (extraction rate, blur/dup thresholds behave sanely), not segmentation accuracy
or real-world coverage behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np


def make_synthetic_video(out_path: str, n_frames: int = 300, fps: float = 30.0, size=(640, 480)):
    w, h = size
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    rng = np.random.default_rng(0)
    static_frame = None
    # A few "checkerboard ground + moving square" frames to emulate parallax motion,
    # then deliberately inject: a run of duplicate (static) frames, and a run of
    # heavily blurred frames, so the filter has something real to catch.
    for i in range(n_frames):
        frame = np.full((h, w, 3), 40, dtype=np.uint8)
        # checkerboard "ground"
        cell = 40
        for gy in range(0, h, cell):
            for gx in range(0, w, cell):
                if ((gx // cell) + (gy // cell)) % 2 == 0:
                    frame[gy:gy + cell, gx:gx + cell] = (60, 90, 60)

        # moving "building" block drifting across frame = parallax stand-in
        bx = int((i / n_frames) * (w - 80))
        cv2.rectangle(frame, (bx, h // 2 - 40), (bx + 80, h // 2 + 40), (120, 60, 60), -1)
        cv2.putText(frame, f"f{i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        if 100 <= i < 130:
            # inject a static duplicate run (simulates hovering)
            if static_frame is None:
                static_frame = frame.copy()
            frame = static_frame.copy()

        if 200 <= i < 220:
            # inject heavy blur (simulates motion blur during a fast turn)
            frame = cv2.GaussianBlur(frame, (25, 25), 15)

        writer.write(frame)
    writer.release()
    print(f"Wrote {n_frames} frames to {out_path}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/datasets/synthetic_test_flight.mp4"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    make_synthetic_video(out)
