from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .coverage_engine import CategoricalCoverageReport
from .georeference_accuracy import GeoreferenceAccuracyMetrics
from .scale_accuracy import ScaleAccuracyMetrics
from .trajectory_accuracy import TrajectoryAccuracyMetrics


@dataclass
class ModelQualityReport:
    dataset_name: str
    scale_error_pct: float
    scale_precision_pct: float
    horizontal_geolocation_rmse_m: float
    vertical_geolocation_rmse_m: float
    position_3d_rmse_m: float
    ate_rmse_m: float
    mean_reprojection_error_px: float
    registered_frames_pct: float
    high_confidence_points_pct: float
    coverage: CategoricalCoverageReport

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def format_summary_table(self) -> str:
        """Formats the official DEFENSE / NTRO Model Quality Report table."""
        lines = [
            "================================================================",
            "                   MODEL QUALITY REPORT                         ",
            "================================================================",
            f"Dataset:                         {self.dataset_name}",
            f"Scale Error:                     {self.scale_error_pct:.2f}%",
            f"Scale Precision:                 {self.scale_precision_pct:.2f}%",
            f"Horizontal Geolocation (XY):     {self.horizontal_geolocation_rmse_m:.2f} m",
            f"Vertical Geolocation (Z):       {self.vertical_geolocation_rmse_m:.2f} m",
            f"Absolute Trajectory (ATE RMSE):  {self.ate_rmse_m:.2f} m",
            f"Mean Reprojection Error:         {self.mean_reprojection_error_px:.3f} px",
            f"Registered Keyframes:            {self.registered_frames_pct:.1f}%",
            f"High-Confidence Points:          {self.high_confidence_points_pct:.1f}%",
            "----------------------------------------------------------------",
            "SURFACE OBSERVATION & COVERAGE:",
            f"  Observed Surface:              {self.coverage.overall_coverage_pct:.1f}%",
            f"  High Confidence Observed:      {self.coverage.high_confidence_observed_pct:.1f}%",
            f"  Weak / Low Confidence:         {self.coverage.low_confidence_observed_pct:.1f}%",
            f"  Unobserved (Self-Occluded):    {self.coverage.unobserved_occluded_pct:.1f}%",
            f"  Unobserved (Outside FOV):      {self.coverage.unobserved_outside_fov_pct:.1f}%",
            "----------------------------------------------------------------",
            "CATEGORICAL COVERAGE BREAKDOWN:",
        ]
        for cat in self.coverage.category_breakdown:
            lines.append(f"  {cat.category:<25}: {cat.coverage_ratio_pct:.1f}% ({cat.observed_elements}/{cat.total_elements})")
        lines.append("================================================================")
        return "\n".join(lines)


def generate_quality_report(
    dataset_name: str,
    scale_metrics: ScaleAccuracyMetrics,
    geo_metrics: GeoreferenceAccuracyMetrics,
    trajectory_metrics: TrajectoryAccuracyMetrics,
    mean_reproj_px: float,
    registered_frames_pct: float,
    high_conf_pct: float,
    coverage: CategoricalCoverageReport,
) -> ModelQualityReport:
    """Factory helper to instantiate a complete ModelQualityReport."""
    return ModelQualityReport(
        dataset_name=dataset_name,
        scale_error_pct=scale_metrics.scale_error_pct,
        scale_precision_pct=scale_metrics.scale_precision_pct,
        horizontal_geolocation_rmse_m=geo_metrics.horizontal_rmse_m,
        vertical_geolocation_rmse_m=geo_metrics.vertical_rmse_m,
        position_3d_rmse_m=geo_metrics.position_3d_rmse_m,
        ate_rmse_m=trajectory_metrics.ate_rmse_m,
        mean_reprojection_error_px=mean_reproj_px,
        registered_frames_pct=registered_frames_pct,
        high_confidence_points_pct=high_conf_pct,
        coverage=coverage,
    )
