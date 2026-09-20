from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .flight_session import FlightSession, GPSFix, IMUMeasurement


@dataclass
class TrajectoryState:
    timestamp: float
    position_enu: np.ndarray        # shape (3,) [East, North, Up] in meters
    velocity_enu: np.ndarray        # shape (3,) in m/s
    rotation_matrix: np.ndarray     # shape (3, 3) body to ENU rotation
    position_covariance: np.ndarray # shape (3, 3) variance/covariance in m^2


class EKFTrajectoryEstimator:
    """Continuous 6-DoF Extended Kalman Filter fusing IMU kinematics with GPS fixes and barometric altitude."""

    def __init__(
        self,
        accel_noise: float = 0.2,       # m/s^2 / sqrt(Hz)
        gyro_noise: float = 0.02,       # rad/s / sqrt(Hz)
        gps_pos_noise: float = 1.0,     # m (horizontal standard deviation)
        baro_alt_noise: float = 0.5,    # m (vertical standard deviation)
        gravity_m_s2: float = 9.80665,
    ):
        self.accel_noise = accel_noise
        self.gyro_noise = gyro_noise
        self.gps_pos_noise = gps_pos_noise
        self.baro_alt_noise = baro_alt_noise
        self.gravity = gravity_m_s2

        # State: [px, py, pz, vx, vy, vz, roll, pitch, yaw] (9x1)
        self.state = np.zeros(9, dtype=np.float64)
        self.cov = np.eye(9, dtype=np.float64) * 1.0
        self.cov[0:3, 0:3] *= 4.0   # initial position uncertainty
        self.cov[3:6, 3:6] *= 1.0   # initial velocity uncertainty
        self.cov[6:9, 6:9] *= 0.1   # initial orientation uncertainty

        self.initialized_position = False
        self.last_timestamp: float | None = None

    def _euler_to_rotmat(self, roll: float, pitch: float, yaw: float) -> np.ndarray:
        """Body to World (ENU) rotation matrix (ZYX convention)."""
        cr, sr = np.cos(roll), np.sin(roll)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)

        R_x = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
        R_y = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
        R_z = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
        return R_z @ R_y @ R_x

    def predict(self, imu: IMUMeasurement) -> None:
        """Propagates state forward by dt using high-rate IMU accelerations and angular rates."""
        if self.last_timestamp is None:
            self.last_timestamp = imu.timestamp
            return

        dt = imu.timestamp - self.last_timestamp
        if dt <= 0.0 or dt > 1.0:
            # Skip invalid or massive time steps
            self.last_timestamp = imu.timestamp
            return

        roll, pitch, yaw = self.state[6:9]
        R_b_w = self._euler_to_rotmat(roll, pitch, yaw)

        # Transform body acceleration to world (ENU) frame and subtract gravity
        accel_b = np.array(imu.accel_xyz, dtype=np.float64)
        accel_w = R_b_w @ accel_b - np.array([0.0, 0.0, self.gravity], dtype=np.float64)

        # Position & Velocity kinematic update
        self.state[0:3] += self.state[3:6] * dt + 0.5 * accel_w * (dt**2)
        self.state[3:6] += accel_w * dt

        # Orientation rate update (approximate for moderate angles)
        gyro_b = np.array(imu.gyro_xyz, dtype=np.float64)
        self.state[6:9] += gyro_b * dt

        # State transition Jacobian F
        F = np.eye(9, dtype=np.float64)
        F[0:3, 3:6] = np.eye(3) * dt

        # Process noise covariance Q
        Q = np.eye(9, dtype=np.float64)
        Q[0:3, 0:3] *= (0.5 * self.accel_noise * (dt**2))**2
        Q[3:6, 3:6] *= (self.accel_noise * dt)**2
        Q[6:9, 6:9] *= (self.gyro_noise * dt)**2

        self.cov = F @ self.cov @ F.T + Q
        self.last_timestamp = imu.timestamp

    def update_gps(self, pos_enu: np.ndarray, horizontal_accuracy_m: float = 1.0) -> None:
        """Measurement update using GPS absolute position in ENU frame."""
        R = np.eye(3, dtype=np.float64) * (horizontal_accuracy_m**2)
        R[2, 2] *= 2.0  # Vertical GPS accuracy typically 2x worse than horizontal

        if not self.initialized_position:
            self.state[0:3] = pos_enu
            self.cov[0:3, 0:3] = R
            self.initialized_position = True
            return

        H = np.zeros((3, 9), dtype=np.float64)
        H[0:3, 0:3] = np.eye(3)

        y = pos_enu - H @ self.state
        S = H @ self.cov @ H.T + R
        K = self.cov @ H.T @ np.linalg.inv(S)

        self.state += K @ y
        I_KH = np.eye(9) - K @ H
        self.cov = I_KH @ self.cov @ I_KH.T + K @ R @ K.T

    def update_barometer(self, alt_enu_m: float, baro_accuracy_m: float = 0.5) -> None:
        """Measurement update using barometric altitude in ENU Up coordinate."""
        H = np.zeros((1, 9), dtype=np.float64)
        H[0, 2] = 1.0  # measures Z (Up)

        R = np.array([[baro_accuracy_m**2]], dtype=np.float64)

        y = np.array([alt_enu_m]) - H @ self.state
        S = H @ self.cov @ H.T + R
        K = self.cov @ H.T @ np.linalg.inv(S)

        self.state += (K @ y).flatten()
        I_KH = np.eye(9) - K @ H
        self.cov = I_KH @ self.cov @ I_KH.T + K @ R @ K.T

    def get_state(self, timestamp: float) -> TrajectoryState:
        roll, pitch, yaw = self.state[6:9]
        return TrajectoryState(
            timestamp=timestamp,
            position_enu=self.state[0:3].copy(),
            velocity_enu=self.state[3:6].copy(),
            rotation_matrix=self._euler_to_rotmat(roll, pitch, yaw),
            position_covariance=self.cov[0:3, 0:3].copy(),
        )

    @classmethod
    def estimate_trajectory(cls, session: FlightSession) -> list[TrajectoryState]:
        """Runs continuous forward fusion across the synchronized FlightSession."""
        estimator = cls()
        if not session.frames:
            return []

        # If no GPS fixes, return trajectory states from frame position if available
        if not session.gps_fixes and not session.imu_measurements:
            return [
                TrajectoryState(
                    timestamp=f.timestamp,
                    position_enu=np.array(f.position_enu if f.position_enu else (0.0, 0.0, 0.0)),
                    velocity_enu=np.zeros(3),
                    rotation_matrix=np.eye(3),
                    position_covariance=np.eye(3),
                )
                for f in session.frames
            ]

        # Combine all telemetry events into a sorted event stream
        events: list[tuple[float, str, object]] = []
        for imu in session.imu_measurements:
            events.append((imu.timestamp, "IMU", imu))
        for f in session.frames:
            if f.position_enu is not None:
                events.append((f.timestamp, "GPS", np.array(f.position_enu)))
            if f.barometer is not None:
                events.append((f.timestamp, "BARO", f.barometer.altitude_m))
            events.append((f.timestamp, "FRAME", f))

        events.sort(key=lambda x: x[0])

        trajectory: list[TrajectoryState] = []
        for ts, ev_type, data in events:
            if ev_type == "IMU":
                estimator.predict(data)  # type: ignore
            elif ev_type == "GPS":
                estimator.update_gps(data)  # type: ignore
            elif ev_type == "BARO":
                estimator.update_barometer(data)  # type: ignore
            elif ev_type == "FRAME":
                trajectory.append(estimator.get_state(ts))

        return trajectory
