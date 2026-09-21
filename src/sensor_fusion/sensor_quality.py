from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np


class GPSQualityTier(str, Enum):
    STRONG_GPS = "STRONG_GPS"                    # High BNR >= 3.0, robust georeferencing
    WEAK_GPS = "WEAK_GPS"                        # 0.5 <= BNR < 3.0, downweighted prior
    INSUFFICIENT_BASELINE = "INSUFFICIENT_BASELINE"  # BNR < 0.5, trajectory smaller than noise (e.g. hover)
    LOCAL_METRIC = "LOCAL_METRIC"                # No GPS available, pure visual-inertial local frame


@dataclass
class SensorQualityReport:
    total_fixes: int
    valid_fixes: int
    horizontal_spread_m: float
    vertical_spread_m: float
    trajectory_baseline_m: float
    estimated_noise_m: float
    baseline_to_noise_ratio: float
    quality_tier: GPSQualityTier
    recommended_gps_weight: float
    recommended_mode: str
    has_imu: bool = False
    has_barometer: bool = False
    summary: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["quality_tier"] = self.quality_tier.value
        return d


class SensorQualityEvaluator:
    """Evaluates GPS/IMU quality and baseline-to-noise ratio (BNR) to prevent
    unconstrained similarity alignment from diverging when drone translation is smaller
    than consumer GPS noise (e.g., hover or short baseline flights)."""

    def __init__(
        self,
        default_gps_noise_m: float = 6.0,
        rtk_gps_noise_m: float = 0.05,
    ):
        self.default_gps_noise_m = default_gps_noise_m
        self.rtk_gps_noise_m = rtk_gps_noise_m

    def evaluate_trajectory(
        self,
        enu_positions: np.ndarray | None,
        is_rtk: bool = False,
        has_imu: bool = False,
        has_barometer: bool = False,
    ) -> SensorQualityReport:
        """Evaluates an (N, 3) array of ENU positions (in meters).
        
        Args:
            enu_positions: (N, 3) positions in East-North-Up coordinates (meters), or None.
            is_rtk: Whether the sensor is RTK-grade (sub-decimeter noise).
            has_imu: Whether high-rate IMU is present in telemetry.
            has_barometer: Whether barometric altitude is present.
        """
        if enu_positions is None or len(enu_positions) == 0:
            return SensorQualityReport(
                total_fixes=0,
                valid_fixes=0,
                horizontal_spread_m=0.0,
                vertical_spread_m=0.0,
                trajectory_baseline_m=0.0,
                estimated_noise_m=self.default_gps_noise_m,
                baseline_to_noise_ratio=0.0,
                quality_tier=GPSQualityTier.LOCAL_METRIC,
                recommended_gps_weight=0.0,
                recommended_mode="LOCAL_METRIC",
                has_imu=has_imu,
                has_barometer=has_barometer,
                summary="No GPS fixes available. Operating in pure LOCAL_METRIC mode.",
            )

        # Filter NaNs or infs
        valid_mask = ~np.isnan(enu_positions).any(axis=1) & ~np.isinf(enu_positions).any(axis=1)
        valid_positions = enu_positions[valid_mask]
        n_valid = len(valid_positions)
        n_total = len(enu_positions)

        if n_valid < 2:
            return SensorQualityReport(
                total_fixes=n_total,
                valid_fixes=n_valid,
                horizontal_spread_m=0.0,
                vertical_spread_m=0.0,
                trajectory_baseline_m=0.0,
                estimated_noise_m=self.default_gps_noise_m,
                baseline_to_noise_ratio=0.0,
                quality_tier=GPSQualityTier.LOCAL_METRIC,
                recommended_gps_weight=0.0,
                recommended_mode="LOCAL_METRIC",
                has_imu=has_imu,
                has_barometer=has_barometer,
                summary="Insufficient valid GPS fixes (< 2). Reverting to LOCAL_METRIC mode.",
            )

        # Compute spatial extents
        e = valid_positions[:, 0]
        n = valid_positions[:, 1]
        u = valid_positions[:, 2]

        e_span = float(np.ptp(e))
        n_span = float(np.ptp(n))
        h_spread = float(np.sqrt(e_span**2 + n_span**2))
        v_spread = float(np.ptp(u))

        # Trajectory baseline (max distance between any pairs or first/last & extrema)
        diffs = valid_positions - valid_positions[0:1]
        distances_from_origin = np.linalg.norm(diffs[:, :2], axis=1)
        trajectory_baseline = float(np.max(distances_from_origin))

        noise_m = self.rtk_gps_noise_m if is_rtk else self.default_gps_noise_m
        bnr = trajectory_baseline / max(noise_m, 1e-6)

        # Tier assignment
        if bnr >= 3.0:
            tier = GPSQualityTier.STRONG_GPS
            gps_weight = 1.0
            mode = "STRONG_GPS"
            summary = (
                f"Trajectory baseline ({trajectory_baseline:.1f}m) exceeds sensor noise ({noise_m:.1f}m). "
                f"BNR = {bnr:.2f} >= 3.0. GPS alignment is robust and metric."
            )
        elif bnr >= 0.5:
            tier = GPSQualityTier.WEAK_GPS
            # Smooth scaling from 0.05 to 0.5 based on BNR
            gps_weight = float(np.clip(0.05 + 0.18 * (bnr - 0.5), 0.05, 0.5))
            mode = "WEAK_GPS"
            summary = (
                f"Moderate trajectory baseline ({trajectory_baseline:.1f}m) relative to noise ({noise_m:.1f}m). "
                f"BNR = {bnr:.2f}. Visual trajectory is primary; GPS applied as weak prior."
            )
        else:
            tier = GPSQualityTier.INSUFFICIENT_BASELINE
            gps_weight = 0.01
            mode = "INSUFFICIENT_BASELINE"
            summary = (
                f"Trajectory baseline ({trajectory_baseline:.1f}m) is smaller than GPS noise ({noise_m:.1f}m). "
                f"BNR = {bnr:.2f} < 0.5. Similarity alignment unconstrained would diverge. "
                f"Visual scale is locked; GPS used strictly for translation origin."
            )

        return SensorQualityReport(
            total_fixes=n_total,
            valid_fixes=n_valid,
            horizontal_spread_m=round(h_spread, 3),
            vertical_spread_m=round(v_spread, 3),
            trajectory_baseline_m=round(trajectory_baseline, 3),
            estimated_noise_m=round(noise_m, 3),
            baseline_to_noise_ratio=round(bnr, 3),
            quality_tier=tier,
            recommended_gps_weight=round(gps_weight, 4),
            recommended_mode=mode,
            has_imu=has_imu,
            has_barometer=has_barometer,
            summary=summary,
        )
