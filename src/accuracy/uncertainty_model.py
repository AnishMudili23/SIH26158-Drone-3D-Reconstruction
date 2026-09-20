from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import numpy as np


class ConfidenceTier(str, Enum):
    HIGH = "high"          # Green (C >= 0.70)
    MEDIUM = "medium"      # Yellow (0.40 <= C < 0.70)
    LOW = "low"            # Red (0.10 <= C < 0.40)
    UNOBSERVED = "unobserved"  # Gray (C < 0.10)


@dataclass
class PointUncertaintyScore:
    total_confidence: float          # [0.0, 1.0]
    tier: ConfidenceTier             # HIGH, MEDIUM, LOW, UNOBSERVED
    reprojection_score: float        # based on reprojection error px
    track_length_score: float        # based on number of observing cameras
    depth_consistency_score: float   # based on multi-view depth agreement
    sensor_agreement_score: float    # based on GPS/IMU consistency


class MultiFactorUncertaintyModel:
    """Multi-factor uncertainty modeling combining classical SfM geometry,
    multi-view depth consistency, and sensor agreement into an interpretable [0, 1] confidence score."""

    def __init__(
        self,
        weight_reprojection: float = 0.30,
        weight_track_len: float = 0.25,
        weight_depth_consistency: float = 0.25,
        weight_sensor_agreement: float = 0.20,
    ):
        self.w_reproj = weight_reprojection
        self.w_track = weight_track_len
        self.w_depth = weight_depth_consistency
        self.w_sensor = weight_sensor_agreement

    def evaluate_points(
        self,
        reprojection_errors_px: np.ndarray,
        track_lengths: np.ndarray,
        depth_consistency_scores: np.ndarray | None = None,
        sensor_agreement_residuals_m: np.ndarray | None = None,
    ) -> list[PointUncertaintyScore]:
        """Evaluates uncertainty for an array of 3D points.
        
        Args:
            reprojection_errors_px: (N,) array of reprojection residuals in pixels
            track_lengths: (N,) array of number of observing camera frames
            depth_consistency_scores: (N,) optional array in [0.0, 1.0]
            sensor_agreement_residuals_m: (N,) optional array of distance residuals to GPS fixes
        """
        n = len(reprojection_errors_px)
        if n == 0:
            return []

        # 1. Reprojection score: 1.0 at 0 px error, 0.0 at >= 2.0 px error
        s_reproj = np.clip(1.0 - (reprojection_errors_px / 2.0), 0.0, 1.0)

        # 2. Track length score: 1.0 at >= 6 views, 0.0 at < 2 views
        s_track = np.clip((track_lengths - 2.0) / 4.0, 0.0, 1.0)

        # 3. Depth consistency score: default 0.8 if unmeasured
        if depth_consistency_scores is not None:
            s_depth = np.clip(depth_consistency_scores, 0.0, 1.0)
        else:
            s_depth = np.full(n, 0.80, dtype=np.float32)

        # 4. Sensor agreement score: 1.0 at 0m residual, 0.0 at >= 3.0m
        if sensor_agreement_residuals_m is not None:
            s_sensor = np.clip(1.0 - (sensor_agreement_residuals_m / 3.0), 0.0, 1.0)
        else:
            s_sensor = np.full(n, 0.90, dtype=np.float32)

        # Weighted total confidence
        total = (
            self.w_reproj * s_reproj
            + self.w_track * s_track
            + self.w_depth * s_depth
            + self.w_sensor * s_sensor
        )

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

            results.append(PointUncertaintyScore(
                total_confidence=c,
                tier=tier,
                reprojection_score=float(s_reproj[i]),
                track_length_score=float(s_track[i]),
                depth_consistency_score=float(s_depth[i]),
                sensor_agreement_score=float(s_sensor[i]),
            ))

        return results
