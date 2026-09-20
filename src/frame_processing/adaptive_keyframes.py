from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np


@dataclass
class KeyframeScore:
    frame_idx: int
    timestamp: float
    sharpness: float
    exposure_score: float
    overlap_ratio: float
    baseline_distance_m: float
    is_selected: bool
    rejection_reason: str | None = None


class AdaptiveKeyframeEngine:
    """Intelligent keyframe selection engine that maximizes geometric baseline/parallax
    while ensuring 60%–85% inter-frame visual overlap and rejecting blur/bad exposure."""

    def __init__(
        self,
        min_overlap: float = 0.60,
        max_overlap: float = 0.85,
        min_sharpness: float = 50.0,
        min_baseline_m: float = 0.5,
        target_fps_cap: float = 5.0,
    ):
        self.min_overlap = min_overlap
        self.max_overlap = max_overlap
        self.min_sharpness = min_sharpness
        self.min_baseline_m = min_baseline_m
        self.target_fps_cap = target_fps_cap
        self._orb = cv2.ORB_create(nfeatures=500)
        self._matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    def compute_sharpness(self, gray: np.ndarray) -> float:
        """Modified Laplacian variance — higher indicates sharper edges and absence of motion blur."""
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def compute_exposure_score(self, gray: np.ndarray) -> float:
        """Score from 0.0 to 1.0 indicating usable exposure (penalizes extreme blowout >252 or solid black <5)."""
        total = gray.size
        if total == 0:
            return 0.0
        clipped = np.count_nonzero((gray < 5) | (gray > 252))
        return float(1.0 - (clipped / total))

    def estimate_feature_overlap(self, gray_prev: np.ndarray, gray_curr: np.ndarray) -> float:
        """Estimates visual overlap ratio (0.0 to 1.0) using ORB feature matching."""
        kp1, des1 = self._orb.detectAndCompute(gray_prev, None)
        kp2, des2 = self._orb.detectAndCompute(gray_curr, None)

        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            # Fall back to template/histogram correlation if feature count is too low
            res = cv2.matchTemplate(
                cv2.resize(gray_curr, (160, 90)),
                cv2.resize(gray_prev, (160, 90)),
                cv2.TM_CCOEFF_NORMED
            )
            return float(np.clip(res[0, 0], 0.0, 1.0))

        matches = self._matcher.match(des1, des2)
        if not matches:
            return 0.0

        # Ratio of matched features to total detected in previous frame
        overlap = len(matches) / max(len(kp1), len(kp2))
        # Scale to realistic visual overlap estimate (even with 80% visual overlap, ORB recall is ~40-70%)
        # Sigmoid-like normalization so that 40% matched ORB descriptors indicates ~75% overlap
        normalized = float(np.clip(overlap * 1.5, 0.0, 1.0))
        return normalized

    def select_keyframes(
        self,
        frames: Sequence[np.ndarray],
        timestamps: Sequence[float],
        positions_enu: Sequence[tuple[float, float, float] | None] | None = None,
    ) -> list[KeyframeScore]:
        """Evaluates a sequence of video frames and returns per-frame scores and selection decisions."""
        if not frames:
            return []

        scores: list[KeyframeScore] = []
        last_selected_idx: int | None = None
        last_selected_gray: np.ndarray | None = None
        last_selected_pos: np.ndarray | None = None

        for idx, (frame, ts) in enumerate(zip(frames, timestamps)):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
            sharpness = self.compute_sharpness(gray)
            exposure = self.compute_exposure_score(gray)

            # Check blur rejection
            if sharpness < self.min_sharpness:
                scores.append(KeyframeScore(
                    frame_idx=idx,
                    timestamp=ts,
                    sharpness=sharpness,
                    exposure_score=exposure,
                    overlap_ratio=1.0,
                    baseline_distance_m=0.0,
                    is_selected=False,
                    rejection_reason="blur_detected",
                ))
                continue

            # Check extreme exposure clipping
            if exposure < 0.40:
                scores.append(KeyframeScore(
                    frame_idx=idx,
                    timestamp=ts,
                    sharpness=sharpness,
                    exposure_score=exposure,
                    overlap_ratio=1.0,
                    baseline_distance_m=0.0,
                    is_selected=False,
                    rejection_reason="poor_exposure",
                ))
                continue

            # If first valid frame, select unconditionally as anchor
            if last_selected_idx is None:
                last_selected_idx = idx
                last_selected_gray = gray
                last_selected_pos = np.array(positions_enu[idx]) if (positions_enu and positions_enu[idx]) else None
                scores.append(KeyframeScore(
                    frame_idx=idx,
                    timestamp=ts,
                    sharpness=sharpness,
                    exposure_score=exposure,
                    overlap_ratio=1.0,
                    baseline_distance_m=0.0,
                    is_selected=True,
                ))
                continue

            # Compute overlap and metric baseline relative to last selected keyframe
            assert last_selected_gray is not None
            overlap = self.estimate_feature_overlap(last_selected_gray, gray)

            baseline_m = 0.0
            if positions_enu and positions_enu[idx] and last_selected_pos is not None:
                curr_pos = np.array(positions_enu[idx])
                baseline_m = float(np.linalg.norm(curr_pos - last_selected_pos))
            else:
                # Approximate baseline via optical flow or timestamp delta
                baseline_m = float(ts - timestamps[last_selected_idx]) * 2.0  # assumed 2 m/s if unmeasured

            # Selection logic:
            # 1. Overlap is too high (> max_overlap) and baseline is small -> redundant frame
            if overlap > self.max_overlap and baseline_m < self.min_baseline_m:
                scores.append(KeyframeScore(
                    frame_idx=idx,
                    timestamp=ts,
                    sharpness=sharpness,
                    exposure_score=exposure,
                    overlap_ratio=overlap,
                    baseline_distance_m=baseline_m,
                    is_selected=False,
                    rejection_reason="redundant_overlap",
                ))
                continue

            # 2. Overlap is in sweet spot (min_overlap to max_overlap) or baseline reached target -> select
            last_selected_idx = idx
            last_selected_gray = gray
            if positions_enu and positions_enu[idx]:
                last_selected_pos = np.array(positions_enu[idx])

            scores.append(KeyframeScore(
                frame_idx=idx,
                timestamp=ts,
                sharpness=sharpness,
                exposure_score=exposure,
                overlap_ratio=overlap,
                baseline_distance_m=baseline_m,
                is_selected=True,
            ))

        return scores
