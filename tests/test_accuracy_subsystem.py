import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from accuracy.benchmark import ModelQualityReport, generate_quality_report
from accuracy.coverage_engine import CoverageEngine
from accuracy.georeference_accuracy import compute_georeference_accuracy, GeoreferenceAccuracyMetrics
from accuracy.scale_accuracy import compute_scale_accuracy, ScaleAccuracyMetrics
from accuracy.trajectory_accuracy import compute_ate_rmse, compute_rpe, TrajectoryAccuracyMetrics
from accuracy.uncertainty_model import ConfidenceTier, MultiFactorUncertaintyModel


def test_trajectory_ate_and_rpe():
    # Ground truth: linear flight path 0 to 100m along X
    x = np.linspace(0, 100, 20)
    gt = np.stack([x, np.zeros_like(x), np.full_like(x, 50.0)], axis=1)

    # Estimated: scaled by 1.05 and shifted by [10, 5, -2]
    est = gt * 1.05 + np.array([10.0, 5.0, -2.0])

    # With alignment, ATE RMSE should be near zero because it recovers scale, rotation, translation
    ate_rmse, mean_err, max_err = compute_ate_rmse(est, gt, align_trajectories=True)
    assert ate_rmse < 1e-4

    # Relative pose error check
    rpe = compute_rpe(gt, gt, step=1)
    assert rpe == 0.0


def test_scale_accuracy():
    err_pct, precision = compute_scale_accuracy(estimated_scale=1.02, true_scale=1.00)
    assert np.isclose(err_pct, 2.0)
    assert np.isclose(precision, 98.0)


def test_georeference_accuracy():
    gt_enu = np.array([[0.0, 0.0, 10.0], [10.0, 0.0, 10.0]])
    # Estimated has 1.0m horizontal error (dy=1.0) and 2.0m vertical error (dz=2.0)
    est_enu = np.array([[0.0, 1.0, 12.0], [10.0, 1.0, 12.0]])

    metrics = compute_georeference_accuracy(est_enu, gt_enu)
    assert np.isclose(metrics.horizontal_rmse_m, 1.0)
    assert np.isclose(metrics.vertical_rmse_m, 2.0)
    assert np.isclose(metrics.position_3d_rmse_m, np.sqrt(1.0 + 4.0))


def test_coverage_engine():
    points = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [2.0, 2.0, 5.0],
        [3.0, 3.0, 5.0],
    ])
    classes = ["Road", "Road", "Building", "Building"]
    # 3 points high confidence, 1 unobserved
    conf = np.array([0.9, 0.8, 0.75, 0.05])

    rep = CoverageEngine.compute_categorical_coverage(points, classes, conf)
    assert np.isclose(rep.overall_coverage_pct, 75.0)
    assert np.isclose(rep.high_confidence_observed_pct, 75.0)
    assert len(rep.category_breakdown) == 5


def test_multifactor_uncertainty_model():
    model = MultiFactorUncertaintyModel()
    reproj = np.array([0.1, 1.8, 0.2])
    tracks = np.array([10.0, 2.0, 3.0])

    scores = model.evaluate_points(reproj, tracks)
    assert len(scores) == 3
    # Point 0: low reproj error, high track length -> HIGH tier
    assert scores[0].tier == ConfidenceTier.HIGH
    assert scores[0].total_confidence >= 0.70
    assert scores[0].depth_consistency_score is None
    assert scores[0].sensor_agreement_score is None
    # Point 1: high reproj error (1.8px), min track length (2 views) -> truthfully UNOBSERVED/LOW without fake defaults
    assert scores[1].tier in (ConfidenceTier.LOW, ConfidenceTier.UNOBSERVED)
    assert scores[1].total_confidence < 0.40



def test_quality_report_formatting():
    scale_m = ScaleAccuracyMetrics(2.1, 97.9, 0.05, 0.12, 10)
    geo_m = GeoreferenceAccuracyMetrics(1.8, 2.7, 3.25, 2.1, 3.0, 10)
    traj_m = TrajectoryAccuracyMetrics(0.85, 0.72, 1.2, 0.15, 0.5, 50)
    cov = CoverageEngine.compute_categorical_coverage(
        np.zeros((10, 3)), ["Road"] * 10, np.full(10, 0.85)
    )

    report = generate_quality_report(
        dataset_name="TestFlight_001",
        scale_metrics=scale_m,
        geo_metrics=geo_m,
        trajectory_metrics=traj_m,
        mean_reproj_px=0.43,
        registered_frames_pct=98.4,
        high_conf_pct=84.2,
        coverage=cov,
    )

    table = report.format_summary_table()
    assert "MODEL QUALITY REPORT" in table
    assert "Scale Error:                     2.10%" in table
    assert "Horizontal Geolocation (XY):     1.80 m" in table
