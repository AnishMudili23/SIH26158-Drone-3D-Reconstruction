import numpy as np
import pytest
from src.sensor_fusion.sensor_quality import (
    GPSQualityTier,
    SensorQualityEvaluator,
)


def test_sensor_quality_no_gps():
    evaluator = SensorQualityEvaluator()
    rep = evaluator.evaluate_trajectory(None)
    assert rep.quality_tier == GPSQualityTier.LOCAL_METRIC
    assert rep.recommended_gps_weight == 0.0
    assert rep.recommended_mode == "LOCAL_METRIC"


def test_sensor_quality_insufficient_baseline_hover():
    # Synthetic hover: drone stays within a 1.6m x 1.7m box with 6m noise (like Zurich MAV subset)
    np.random.seed(42)
    hover_enu = np.random.uniform(-0.8, 0.8, size=(100, 3))
    evaluator = SensorQualityEvaluator(default_gps_noise_m=6.0)
    rep = evaluator.evaluate_trajectory(hover_enu)

    assert rep.quality_tier == GPSQualityTier.INSUFFICIENT_BASELINE
    assert rep.baseline_to_noise_ratio < 0.5
    assert rep.recommended_gps_weight <= 0.05
    assert rep.recommended_mode == "INSUFFICIENT_BASELINE"


def test_sensor_quality_weak_gps():
    # Trajectory baseline 10m, noise 6m -> BNR ~ 1.67
    t = np.linspace(0, 10, 50)
    enu = np.column_stack([t, np.zeros(50), np.zeros(50)])
    evaluator = SensorQualityEvaluator(default_gps_noise_m=6.0)
    rep = evaluator.evaluate_trajectory(enu)

    assert rep.quality_tier == GPSQualityTier.WEAK_GPS
    assert 0.5 <= rep.baseline_to_noise_ratio < 3.0
    assert 0.05 <= rep.recommended_gps_weight <= 0.5


def test_sensor_quality_strong_gps():
    # Long corridor flight: baseline 150m, noise 6m -> BNR 25.0 >= 3.0
    t = np.linspace(0, 150, 100)
    enu = np.column_stack([t, 0.5 * t, np.zeros(100)])
    evaluator = SensorQualityEvaluator(default_gps_noise_m=6.0)
    rep = evaluator.evaluate_trajectory(enu)

    assert rep.quality_tier == GPSQualityTier.STRONG_GPS
    assert rep.baseline_to_noise_ratio >= 3.0
    assert rep.recommended_gps_weight == 1.0


def test_sensor_quality_rtk_grade():
    # Even a 5m baseline with RTK (noise 0.05m) is BNR 100.0 -> STRONG_GPS
    t = np.linspace(0, 5, 20)
    enu = np.column_stack([t, np.zeros(20), np.zeros(20)])
    evaluator = SensorQualityEvaluator()
    rep = evaluator.evaluate_trajectory(enu, is_rtk=True)

    assert rep.quality_tier == GPSQualityTier.STRONG_GPS
    assert rep.baseline_to_noise_ratio > 10.0
