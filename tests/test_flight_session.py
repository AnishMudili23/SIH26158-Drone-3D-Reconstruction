import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telemetry.flight_session import (
    BarometerMeasurement,
    CameraModel,
    FlightSession,
    FrameMetadata,
    GPSFix,
    IMUMeasurement,
    ProvenanceMode,
)
from telemetry.ekf_trajectory import EKFTrajectoryEstimator, TrajectoryState


def test_flight_session_synchronization():
    cam = CameraModel(width=1920, height=1080, fx=1000.0, fy=1000.0, cx=960.0, cy=540.0)

    # 3 frames at 0.0s, 1.0s, 2.0s
    frames = [
        FrameMetadata(frame_idx=0, timestamp=0.0, image_filename="f0.png"),
        FrameMetadata(frame_idx=1, timestamp=1.0, image_filename="f1.png"),
        FrameMetadata(frame_idx=2, timestamp=2.0, image_filename="f2.png"),
    ]

    # GPS fixes at 0.0s and 2.0s (linear path from lat 12.0 to 12.0002)
    gps_fixes = [
        GPSFix(timestamp=0.0, latitude=12.0, longitude=77.0, altitude_m=900.0),
        GPSFix(timestamp=2.0, latitude=12.0002, longitude=77.0, altitude_m=910.0),
    ]

    # IMU measurements at 0.0s, 1.0s, 2.0s
    imu_meas = [
        IMUMeasurement(timestamp=0.0, accel_xyz=(0.0, 0.0, 9.80665), gyro_xyz=(0.0, 0.0, 0.0)),
        IMUMeasurement(timestamp=1.0, accel_xyz=(0.1, 0.0, 9.80665), gyro_xyz=(0.0, 0.0, 0.01)),
        IMUMeasurement(timestamp=2.0, accel_xyz=(0.2, 0.0, 9.80665), gyro_xyz=(0.0, 0.0, 0.02)),
    ]

    session = FlightSession(
        session_id="test_sync_001",
        provenance=ProvenanceMode.REAL,
        camera=cam,
        frames=frames,
        gps_fixes=gps_fixes,
        imu_measurements=imu_meas,
    )

    session.synchronize_telemetry()

    # Frame 1 at t=1.0s should have interpolated GPS latitude = 12.0001 and altitude = 905.0m
    f1 = session.frames[1]
    assert f1.gps is not None
    assert np.isclose(f1.gps.latitude, 12.0001, atol=1e-6)
    assert np.isclose(f1.gps.altitude_m, 905.0, atol=1e-3)
    assert f1.position_enu is not None
    assert len(f1.position_enu) == 3

    # Frame 1 IMU should have interpolated values
    assert f1.imu is not None
    assert np.isclose(f1.imu.accel_xyz[0], 0.1, atol=1e-4)
    assert np.isclose(f1.imu.gyro_xyz[2], 0.01, atol=1e-4)


def test_flight_session_guards_against_fake_gps():
    cam = CameraModel(width=1920, height=1080, fx=1000.0, fy=1000.0, cx=960.0, cy=540.0)
    frames = [
        FrameMetadata(frame_idx=0, timestamp=0.0, image_filename="f0.png"),
        FrameMetadata(frame_idx=1, timestamp=1.0, image_filename="f1.png"),
    ]

    # No GPS fixes passed
    session = FlightSession(
        session_id="no_gps_session",
        provenance=ProvenanceMode.NONE,
        camera=cam,
        frames=frames,
        gps_fixes=[],
    )

    session.synchronize_telemetry()

    assert not session.is_georeferenced
    for f in session.frames:
        assert f.gps is None
        assert f.position_enu is None


def test_flight_session_integrity_validation():
    cam = CameraModel(width=1920, height=1080, fx=1000.0, fy=1000.0, cx=960.0, cy=540.0)

    # Corrupt timestamps (non-monotonic)
    frames = [
        FrameMetadata(frame_idx=0, timestamp=2.0, image_filename="f0.png"),
        FrameMetadata(frame_idx=1, timestamp=1.0, image_filename="f1.png"),
    ]

    session = FlightSession(
        session_id="corrupt_session",
        provenance=ProvenanceMode.REAL,
        camera=cam,
        frames=frames,
    )

    issues = session.validate_integrity()
    assert any("strictly monotonically increasing" in issue for issue in issues)


def test_flight_session_json_roundtrip(tmp_path):
    cam = CameraModel(width=1280, height=720, fx=800.0, fy=800.0, cx=640.0, cy=360.0)
    frames = [FrameMetadata(frame_idx=0, timestamp=0.0, image_filename="f0.png")]
    gps = [GPSFix(timestamp=0.0, latitude=13.0, longitude=77.5, altitude_m=920.0)]

    session = FlightSession(
        session_id="json_test",
        provenance=ProvenanceMode.SIMULATED,
        camera=cam,
        frames=frames,
        gps_fixes=gps,
    )

    save_path = tmp_path / "session.json"
    session.save_json(save_path)

    loaded = FlightSession.load_json(save_path)
    assert loaded.session_id == session.session_id
    assert loaded.provenance == session.provenance
    assert loaded.camera.fx == session.camera.fx
    assert len(loaded.gps_fixes) == 1
    assert loaded.gps_fixes[0].latitude == 13.0


def test_ekf_trajectory_estimator_fusion():
    estimator = EKFTrajectoryEstimator(gravity_m_s2=9.80665)

    # Hovering drone: IMU measures upward gravity acceleration [0, 0, 9.80665]
    # Stationary at ENU [10.0, 20.0, 50.0]
    dt = 0.05
    for step in range(20):
        t = step * dt
        imu = IMUMeasurement(timestamp=t, accel_xyz=(0.0, 0.0, 9.80665), gyro_xyz=(0.0, 0.0, 0.0))
        estimator.predict(imu)

    # Add GPS fix at t=1.0s
    estimator.update_gps(np.array([10.0, 20.0, 50.0]))

    state = estimator.get_state(1.0)
    assert np.allclose(state.position_enu, [10.0, 20.0, 50.0], atol=1.0)
    # Position uncertainty should have converged significantly from initial covariance
    assert state.position_covariance[0, 0] < 4.0
