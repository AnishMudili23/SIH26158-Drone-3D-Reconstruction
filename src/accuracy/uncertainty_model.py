from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np


class ConfidenceTier(str, Enum):
    HIGH = "high"              # Green (C >= 0.70)
    MEDIUM = "medium"          # Yellow (0.40 <= C < 0.70)
    LOW = "low"                # Red (0.10 <= C < 0.40)
    UNOBSERVED = "unobserved"  # Gray (C < 0.10)


@dataclass
class PointUncertaintyScore:
    total_confidence: float               # [0.0, 1.0] dynamically normalized across available signals
    tier: ConfidenceTier                  # HIGH, MEDIUM, LOW, UNOBSERVED
    reprojection_score: float             # based on reprojection error px
    track_length_score: float             # based on number of observing camera frames
    depth_consistency_score: float | None # based on multi-view depth agreement (None if unavailable)
    sensor_agreement_score: float | None  # based on GPS/IMU consistency (None if unavailable)
    semantic_confidence_score: float | None = None  # based on multi-view voting agreement (None if unavailable)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d


class MultiFactorUncertaintyModel:
    """Scientific multi-factor uncertainty modeling. Combines classical SfM geometry,
    multi-view depth consistency, semantic stability, and sensor agreement into an
    interpretable [0, 1] confidence score.
    
    CRITICAL SCIENTIFIC PRINCIPLE:
    Missing modalities are recorded as None/unavailable rather than assigning fake
    high default scores (e.g. 0.80 or 0.90). The total confidence is dynamically
    re-normalized strictly across the signals that were actually measured and verified.
    """

    def __init__(
        self,
        weight_reprojection: float = 0.30,
        weight_track_len: float = 0.25,
        weight_depth_consistency: float = 0.25,
        weight_sensor_agreement: float = 0.20,
        weight_semantic_confidence: float = 0.15,
    ):
        self.w_reproj = weight_reprojection
        self.w_track = weight_track_len
        self.w_depth = weight_depth_consistency
        self.w_sensor = weight_sensor_agreement
        self.w_semantic = weight_semantic_confidence

    def evaluate_points(
        self,
        reprojection_errors_px: np.ndarray,
        track_lengths: np.ndarray,
        depth_consistency_scores: np.ndarray | None = None,
        sensor_agreement_residuals_m: np.ndarray | None = None,
        semantic_confidences: np.ndarray | None = None,
    ) -> list[PointUncertaintyScore]:
        """Evaluates uncertainty for an array of 3D points.
        
        Args:
            reprojection_errors_px: (N,) array of reprojection residuals in pixels.
            track_lengths: (N,) array of number of observing camera frames.
            depth_consistency_scores: (N,) optional array in [0.0, 1.0], or None if unmeasured.
            sensor_agreement_residuals_m: (N,) optional array of distance residuals to GPS fixes, or None.
            semantic_confidences: (N,) optional array in [0.0, 1.0] from multi-view voting, or None.
        """
        n = len(reprojection_errors_px)
        if n == 0:
            return []

        # 1. Reprojection score: 1.0 at 0 px error, 0.0 at >= 2.0 px error
        s_reproj = np.clip(1.0 - (reprojection_errors_px / 2.0), 0.0, 1.0)

        # 2. Track length score: 1.0 at >= 6 views, 0.0 at < 2 views
        s_track = np.clip((track_lengths - 2.0) / 4.0, 0.0, 1.0)

        # Base available weights and signals
        available_weights = self.w_reproj + self.w_track
        weighted_sum = self.w_reproj * s_reproj + self.w_track * s_track

        # 3. Depth consistency score (strictly None when not measured)
        s_depth: np.ndarray | None = None
        if depth_consistency_scores is not None:
            s_depth = np.clip(depth_consistency_scores, 0.0, 1.0)
            weighted_sum += self.w_depth * s_depth
            available_weights += self.w_depth

        # 4. Sensor agreement score (strictly None when not measured)
        s_sensor: np.ndarray | None = None
        if sensor_agreement_residuals_m is not None:
            s_sensor = np.clip(1.0 - (sensor_agreement_residuals_m / 3.0), 0.0, 1.0)
            weighted_sum += self.w_sensor * s_sensor
            available_weights += self.w_sensor

        # 5. Semantic confidence score (strictly None when not measured)
        s_semantic: np.ndarray | None = None
        if semantic_confidences is not None:
            s_semantic = np.clip(semantic_confidences, 0.0, 1.0)
            weighted_sum += self.w_semantic * s_semantic
            available_weights += self.w_semantic

        # Dynamically normalize across available active weights
        norm_factor = max(available_weights, 1e-6)
        total = np.clip(weighted_sum / norm_factor, 0.0, 1.0)

        results: list[PointUncertaintyScore] = []
        for i in range(n):
            c = float(total[i])
            if c >= 0.70:
                tier = ConfidenceTier.HIGH
            elif c >= 0.40:
                tier = ConfidenceTier.MEDIUM
            elif c >= 0.10:
                tier = ConfidenceTier.LOW
            else:
                tier = ConfidenceTier.UNOBSERVED

            depth_val = float(s_depth[i]) if s_depth is not None else None
            sensor_val = float(s_sensor[i]) if s_sensor is not None else None
            semantic_val = float(s_semantic[i]) if s_semantic is not None else None

            results.append(PointUncertaintyScore(
                total_confidence=round(c, 4),
                tier=tier,
                reprojection_score=round(float(s_reproj[i]), 4),
                track_length_score=round(float(s_track[i]), 4),
                depth_consistency_score=round(depth_val, 4) if depth_val is not None else None,
                sensor_agreement_score=round(sensor_val, 4) if sensor_val is not None else None,
                semantic_confidence_score=round(semantic_val, 4) if semantic_val is not None else None,
            ))

        return results
