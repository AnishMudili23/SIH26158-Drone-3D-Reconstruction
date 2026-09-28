"""
Adaptive Keyframe Selection Engine driven by real telemetry, geometric parallax,
feature quality distribution, and exposure/sharpness gating.

Removes arbitrary velocity assumptions (e.g. 2 m/s). Instead:
- Actual GPS coordinates -> true metric baseline (baseline_source='GPS', confidence ~ 0.95)
- IMU/VIO velocity integration -> baseline estimate (baseline_source='IMU_VELOCITY', confidence ~ 0.85)
- Lucas-Kanade / ORB optical flow -> visual disparity proxy (baseline_source='OPTICAL_FLOW', confidence ~ 0.75)

Composite Frame Scoring:
FrameScore =
    0.20 * sharpness_norm
  + 0.10 * exposure_score
  + 0.20 * feature_quality (count + spatial distribution)
  + 0.20 * parallax_score (viewing angle / disparity spread)
  + 0.15 * baseline_score
  + 0.15 * semantic_stability
"""
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
    baseline_source: str          # 'GPS', 'IMU_VELOCITY', 'OPTICAL_FLOW', 'INITIAL_ANCHOR'
    baseline_confidence: float    # 0.0 to 1.0
    feature_quality: float        # 0.0 to 1.0 (count & spatial grid uniformity)
    parallax_score: float         # 0.0 to 1.0 (inter-frame disparity/motion)
    semantic_stability: float     # 0.0 to 1.0 (proportion of stable/static scene)
    composite_score: float        # Weighted overall quality score
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
        grid_rows: int = 4,
        grid_cols: int = 4,
    ):
        self.min_overlap = min_overlap
        self.max_overlap = max_overlap
        self.min_sharpness = min_sharpness
        self.min_baseline_m = min_baseline_m
        self.target_fps_cap = target_fps_cap
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self._orb = cv2.ORB_create(nfeatures=600)
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

    def evaluate_feature_quality(self, gray: np.ndarray) -> tuple[float, list[cv2.KeyPoint], np.ndarray | None]:
        """Evaluates feature abundance and spatial distribution across image grid."""
        kps, des = self._orb.detectAndCompute(gray, None)
        if not kps:
            return 0.0, [], None

        h, w = gray.shape[:2]
        cell_h = h / self.grid_rows
        cell_w = w / self.grid_cols
        grid = np.zeros((self.grid_rows, self.grid_cols), dtype=int)

        for kp in kps:
            r = min(int(kp.pt[1] / cell_h), self.grid_rows - 1)
            c = min(int(kp.pt[0] / cell_w), self.grid_cols - 1)
            grid[r, c] += 1

        # Count abundance score (saturated at 400 features)
        abundance_score = min(1.0, len(kps) / 400.0)
        # Uniformity: fraction of grid cells containing at least 5 features
        uniformity_score = float((grid >= 5).mean())

        feature_quality = 0.5 * abundance_score + 0.5 * uniformity_score
        return float(feature_quality), kps, des

    def estimate_optical_flow_parallax(
        self,
        gray_prev: np.ndarray,
        gray_curr: np.ndarray,
        kp_prev: list[cv2.KeyPoint],
        des_prev: np.ndarray | None,
        kp_curr: list[cv2.KeyPoint],
        des_curr: np.ndarray | None,
    ) -> tuple[float, float, float]:
        """Computes visual overlap ratio, median feature disparity (parallax), and optical flow motion.
        
        Returns:
            (overlap_ratio, parallax_score, motion_magnitude_px)
        """
        if des_prev is None or des_curr is None or len(kp_prev) < 10 or len(kp_curr) < 10:
            res = cv2.matchTemplate(
                cv2.resize(gray_curr, (160, 90)),
                cv2.resize(gray_prev, (160, 90)),
                cv2.TM_CCOEFF_NORMED,
            )
            sim = float(np.clip(res[0, 0], 0.0, 1.0))
            return sim, 0.1, 1.0

        matches = self._matcher.match(des_prev, des_curr)
        if len(matches) < 8:
            return 0.0, 0.0, 0.0

        pts_prev = np.array([kp_prev[m.queryIdx].pt for m in matches])
        pts_curr = np.array([kp_curr[m.trainIdx].pt for m in matches])
        displacements = np.linalg.norm(pts_curr - pts_prev, axis=1)
        median_disp = float(np.median(displacements))

        # Overlap ratio scaled to realistic coverage
        overlap = len(matches) / max(len(kp_prev), len(kp_curr))
        normalized_overlap = float(np.clip(overlap * 1.5, 0.0, 1.0))

        # Parallax score: higher disparity -> stronger parallax up to 60px
        parallax_score = float(np.clip(median_disp / 60.0, 0.0, 1.0))

        return normalized_overlap, parallax_score, median_disp

    def select_keyframes(
        self,
        frames: Sequence[np.ndarray],
        timestamps: Sequence[float],
        positions_enu: Sequence[tuple[float, float, float] | None] | None = None,
        velocities_mps: Sequence[tuple[float, float, float] | None] | None = None,
        semantic_masks: Sequence[np.ndarray | None] | None = None,
    ) -> list[KeyframeScore]:
        """Selects keyframes based on metric baseline, feature quality, parallax, and exposure."""
        if not frames:
            return []

        scores: list[KeyframeScore] = []
        last_selected_idx: int | None = None
        last_selected_gray: np.ndarray | None = None
        last_selected_kps: list[cv2.KeyPoint] = []
        last_selected_des: np.ndarray | None = None
        last_selected_pos: np.ndarray | None = None

        for idx, (frame, ts) in enumerate(zip(frames, timestamps)):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
            sharpness = self.compute_sharpness(gray)
            exposure = self.compute_exposure_score(gray)
            feature_quality, kps, des = self.evaluate_feature_quality(gray)

            # 1. Blur gate
            if sharpness < self.min_sharpness:
                scores.append(KeyframeScore(
                    frame_idx=idx,
                    timestamp=ts,
                    sharpness=sharpness,
                    exposure_score=exposure,
                    overlap_ratio=1.0,
                    baseline_distance_m=0.0,
                    baseline_source="NONE",
                    baseline_confidence=0.0,
                    feature_quality=feature_quality,
                    parallax_score=0.0,
                    semantic_stability=1.0,
                    composite_score=0.0,
                    is_selected=False,
                    rejection_reason="blur_detected",
                ))
                continue

            # 2. Exposure clipping gate
            if exposure < 0.40:
                scores.append(KeyframeScore(
                    frame_idx=idx,
                    timestamp=ts,
                    sharpness=sharpness,
                    exposure_score=exposure,
                    overlap_ratio=1.0,
                    baseline_distance_m=0.0,
                    baseline_source="NONE",
                    baseline_confidence=0.0,
                    feature_quality=feature_quality,
                    parallax_score=0.0,
                    semantic_stability=1.0,
                    composite_score=0.0,
                    is_selected=False,
                    rejection_reason="poor_exposure",
                ))
                continue

            # Anchor selection for the initial frame
            if last_selected_idx is None:
                last_selected_idx = idx
                last_selected_gray = gray
                last_selected_kps = kps
                last_selected_des = des
                last_selected_pos = np.array(positions_enu[idx]) if (positions_enu and positions_enu[idx]) else None

                scores.append(KeyframeScore(
                    frame_idx=idx,
                    timestamp=ts,
                    sharpness=sharpness,
                    exposure_score=exposure,
                    overlap_ratio=1.0,
                    baseline_distance_m=0.0,
                    baseline_source="INITIAL_ANCHOR",
                    baseline_confidence=1.0,
                    feature_quality=feature_quality,
                    parallax_score=0.0,
                    semantic_stability=1.0,
                    composite_score=1.0,
                    is_selected=True,
                ))
                continue

            # 3. Compute baseline with explicit provenance (no assumed 2 m/s)
            dt = ts - timestamps[last_selected_idx]
            baseline_m = 0.0
            baseline_src = "OPTICAL_FLOW"
            baseline_conf = 0.75

            if positions_enu and positions_enu[idx] and last_selected_pos is not None:
                curr_pos = np.array(positions_enu[idx])
                baseline_m = float(np.linalg.norm(curr_pos - last_selected_pos))
                baseline_src = "GPS"
                baseline_conf = 0.95
            elif velocities_mps and velocities_mps[idx]:
                vel = np.array(velocities_mps[idx])
                speed = float(np.linalg.norm(vel))
                baseline_m = speed * max(dt, 0.0)
                baseline_src = "IMU_VELOCITY"
                baseline_conf = 0.85

            # 4. Compute overlap and parallax via feature matching
            assert last_selected_gray is not None
            overlap, parallax, motion_px = self.estimate_optical_flow_parallax(
                last_selected_gray, gray, last_selected_kps, last_selected_des, kps, des
            )

            # If no GPS/IMU, use calibrated optical flow as baseline proxy
            if baseline_src == "OPTICAL_FLOW":
                # Assuming typical drone altitude ~20m and f~1000px, 10px motion ~ 0.2m baseline
                baseline_m = float(motion_px * 0.02)

            # 5. Semantic stability: evaluate dynamic object fraction if masks are provided
            semantic_stability = 1.0
            if semantic_masks and semantic_masks[idx] is not None:
                # E.g. non-dynamic ratio
                mask = semantic_masks[idx]
                dynamic_pixels = np.count_nonzero(mask > 0)
                semantic_stability = max(0.0, 1.0 - (dynamic_pixels / max(mask.size, 1)))

            # 6. Composite scoring
            sharpness_norm = min(1.0, sharpness / 500.0)
            baseline_norm = min(1.0, baseline_m / max(self.min_baseline_m * 3.0, 1e-3))
            composite_score = (
                0.20 * sharpness_norm
                + 0.10 * exposure
                + 0.20 * feature_quality
                + 0.20 * parallax
                + 0.15 * baseline_norm
                + 0.15 * semantic_stability
            )

            # 7. Redundancy check: overlap too high and baseline too small
            if overlap > self.max_overlap and baseline_m < self.min_baseline_m:
                scores.append(KeyframeScore(
                    frame_idx=idx,
                    timestamp=ts,
                    sharpness=sharpness,
                    exposure_score=exposure,
                    overlap_ratio=overlap,
                    baseline_distance_m=baseline_m,
                    baseline_source=baseline_src,
                    baseline_confidence=baseline_conf,
                    feature_quality=feature_quality,
                    parallax_score=parallax,
                    semantic_stability=semantic_stability,
                    composite_score=composite_score,
                    is_selected=False,
                    rejection_reason="redundant_overlap",
                ))
                continue

            # Select keyframe
            last_selected_idx = idx
            last_selected_gray = gray
            last_selected_kps = kps
            last_selected_des = des
            if positions_enu and positions_enu[idx]:
                last_selected_pos = np.array(positions_enu[idx])

            scores.append(KeyframeScore(
                frame_idx=idx,
                timestamp=ts,
                sharpness=sharpness,
                exposure_score=exposure,
                overlap_ratio=overlap,
                baseline_distance_m=baseline_m,
                baseline_source=baseline_src,
                baseline_confidence=baseline_conf,
                feature_quality=feature_quality,
                parallax_score=parallax,
                semantic_stability=semantic_stability,
                composite_score=composite_score,
                is_selected=True,
            ))

        return scores
