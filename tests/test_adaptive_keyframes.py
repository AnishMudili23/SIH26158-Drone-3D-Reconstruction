import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from frame_processing.adaptive_keyframes import AdaptiveKeyframeEngine, KeyframeScore


def test_blurry_frames_rejected():
    engine = AdaptiveKeyframeEngine(min_sharpness=50.0)

    # Sharp synthetic frame with checkerboard
    sharp_img = np.full((200, 200), 50, dtype=np.uint8)
    sharp_img[::20, :] = 200
    sharp_img[:, ::20] = 200

    # Blurred version
    blurry_img = cv2.GaussianBlur(sharp_img, (25, 25), 0)

    frames = [sharp_img, blurry_img, sharp_img]
    timestamps = [0.0, 0.5, 1.0]

    scores = engine.select_keyframes(frames, timestamps)

    assert len(scores) == 3
    assert scores[0].is_selected
    assert not scores[1].is_selected
    assert scores[1].rejection_reason == "blur_detected"


def test_redundant_frames_skipped():
    engine = AdaptiveKeyframeEngine(min_overlap=0.60, max_overlap=0.85, min_baseline_m=1.0)

    # Sharp patterned image
    img = np.full((300, 300), 60, dtype=np.uint8)
    cv2.circle(img, (150, 150), 50, 210, -1)
    cv2.rectangle(img, (50, 50), (100, 100), 180, -1)

    # 4 identical frames simulating a drone hovering stationary
    frames = [img, img.copy(), img.copy(), img.copy()]
    timestamps = [0.0, 0.2, 0.4, 0.6]
    positions = [(0.0, 0.0, 10.0), (0.01, 0.0, 10.0), (0.02, 0.0, 10.0), (0.03, 0.0, 10.0)]

    scores = engine.select_keyframes(frames, timestamps, positions)

    # Frame 0 selected as anchor, frames 1, 2, 3 should be skipped as redundant
    assert scores[0].is_selected
    for s in scores[1:]:
        assert not s.is_selected
        assert s.rejection_reason == "redundant_overlap"


def test_exposure_extremes_filtered():
    engine = AdaptiveKeyframeEngine()

    # Normal patterned image
    good_img = np.random.randint(50, 200, (200, 200), dtype=np.uint8)
    # Underexposed (almost solid black)
    dark_img = np.zeros((200, 200), dtype=np.uint8)

    scores = engine.select_keyframes([dark_img, good_img], [0.0, 0.5])
    assert not scores[0].is_selected
    assert scores[0].rejection_reason == "poor_exposure" or scores[0].rejection_reason == "blur_detected"


def test_telemetry_baseline_source_provenance():
    engine = AdaptiveKeyframeEngine(min_baseline_m=0.5)

    img1 = np.full((200, 200), 100, dtype=np.uint8)
    img1[::20, :] = 250
    img1[:, ::20] = 250
    img2 = np.roll(img1, shift=30, axis=1)

    # 1. With real GPS positions
    positions = [(0.0, 0.0, 50.0), (3.5, 0.0, 50.0)]
    scores = engine.select_keyframes([img1, img2], [0.0, 1.0], positions_enu=positions)
    assert scores[1].baseline_source == "GPS"
    assert scores[1].baseline_confidence >= 0.90
    assert scores[1].baseline_distance_m == pytest.approx(3.5, rel=1e-3)

    # 2. Without GPS (uses optical flow, not assumed 2 m/s velocity)
    scores_nofix = engine.select_keyframes([img1, img2], [0.0, 1.0])
    assert scores_nofix[1].baseline_source == "OPTICAL_FLOW"
    assert scores_nofix[1].baseline_confidence > 0.70
    assert scores_nofix[1].feature_quality > 0.0
    assert scores_nofix[1].composite_score > 0.0
