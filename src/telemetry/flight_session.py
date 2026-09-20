from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from scipy.interpolate import interp1d

from geo.scale_alignment import lla_to_enu


class ProvenanceMode(str, Enum):
    REAL = "REAL"  # Physical UAV sensor logs (e.g. DJI, PX4, ArduPilot, Leica tracker)
    SIMULATED = "SIMULATED"  # Synthetic physics simulator (e.g. AirSim, Gazebo, OpenCV scene)
    ESTIMATED = "ESTIMATED"  # Derived purely from visual odometry / SfM without hardware telemetry
    NONE = "NONE"  # No telemetry available (triggers LOCAL_METRIC mode)


@dataclass
class CameraModel:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    distortion_coeffs: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)
    model_type: str = "PINHOLE"
    rolling_shutter_readout_s: float = 0.0

    def to_intrinsics_matrix(self) -> np.ndarray:
        return np.array([
            [self.fx, 0.0, self.cx],
            [0.0, self.fy, self.cy],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)


@dataclass
class GPSFix:
    timestamp: float  # seconds
    latitude: float   # degrees
    longitude: float  # degrees
    altitude_m: float # WGS84 ellipsoidal or MSL altitude in meters
    horizontal_accuracy_m: float = 1.0
    vertical_accuracy_m: float = 1.5
    fix_type: str = "3D"


@dataclass
class IMUMeasurement:
    timestamp: float  # seconds
    accel_xyz: tuple[float, float, float]  # m/s^2 in body frame
    gyro_xyz: tuple[float, float, float]   # rad/s in body frame


@dataclass
class BarometerMeasurement:
    timestamp: float  # seconds
    pressure_hpa: float
    altitude_m: float


@dataclass
class FrameMetadata:
    frame_idx: int
    timestamp: float  # seconds
    image_filename: str
    gps: GPSFix | None = None
    imu: IMUMeasurement | None = None
    barometer: BarometerMeasurement | None = None
    position_enu: tuple[float, float, float] | None = None


@dataclass
class FlightSession:
    session_id: str
    provenance: ProvenanceMode
    camera: CameraModel
    frames: list[FrameMetadata] = field(default_factory=list)
    gps_fixes: list[GPSFix] = field(default_factory=list)
    imu_measurements: list[IMUMeasurement] = field(default_factory=list)
    barometer_measurements: list[BarometerMeasurement] = field(default_factory=list)
    origin_lla: tuple[float, float, float] | None = None
    crs_epsg: int = 4326

    @property
    def is_georeferenced(self) -> bool:
        return self.provenance in (ProvenanceMode.REAL, ProvenanceMode.SIMULATED) and len(self.gps_fixes) >= 3

    def validate_integrity(self) -> list[str]:
        """Validates timestamp monotonicity, gaps, and telemetry bounds."""
        issues: list[str] = []
        if not self.frames:
            issues.append("FlightSession contains no frames.")

        # Check frame timestamp monotonicity
        frame_ts = [f.timestamp for f in self.frames]
        if any(t2 <= t1 for t1, t2 in zip(frame_ts[:-1], frame_ts[1:])):
            issues.append("Frame timestamps are not strictly monotonically increasing.")

        # Check GPS timestamp monotonicity and gaps
        if self.gps_fixes:
            gps_ts = [g.timestamp for g in self.gps_fixes]
            if any(t2 <= t1 for t1, t2 in zip(gps_ts[:-1], gps_ts[1:])):
                issues.append("GPS timestamps are not strictly monotonically increasing.")
            max_gap = max((t2 - t1 for t1, t2 in zip(gps_ts[:-1], gps_ts[1:])), default=0.0)
            if max_gap > 2.0:
                issues.append(f"GPS telemetry has an abnormal dropout gap of {max_gap:.2f}s (>2.0s).")

        # Check IMU rate
        if self.imu_measurements and len(self.imu_measurements) >= 2:
            dt = np.diff([m.timestamp for m in self.imu_measurements])
            mean_hz = 1.0 / np.mean(dt) if np.mean(dt) > 0 else 0.0
            if mean_hz < 20.0:
                issues.append(f"IMU logging frequency is low ({mean_hz:.1f} Hz; expected >= 50 Hz for trajectory fusion).")

        # Verify provenance vs GPS presence
        if self.provenance == ProvenanceMode.REAL and not self.gps_fixes:
            issues.append("Provenance marked REAL but no GPS fixes are present. Operating in LOCAL_METRIC mode.")

        return issues

    def synchronize_telemetry(self) -> None:
        """Synchronizes high-rate GPS, IMU, and Barometer measurements to exact frame timestamps.
        
        Strict rule: If GPS is missing, coordinates are NOT silently generated with hardcoded
        magic numbers. Instead, position_enu remains None and pipeline is instructed to run in
        LOCAL_METRIC mode.
        """
        if not self.frames:
            return

        frame_timestamps = np.array([f.timestamp for f in self.frames], dtype=np.float64)

        # 1. Synchronize GPS
        if len(self.gps_fixes) >= 2:
            gps_ts = np.array([g.timestamp for g in self.gps_fixes], dtype=np.float64)
            lats = np.array([g.latitude for g in self.gps_fixes], dtype=np.float64)
            lons = np.array([g.longitude for g in self.gps_fixes], dtype=np.float64)
            alts = np.array([g.altitude_m for g in self.gps_fixes], dtype=np.float64)

            # Establish anchor origin if not already set
            if self.origin_lla is None:
                self.origin_lla = (float(lats[0]), float(lons[0]), float(alts[0]))

            interp_lat = interp1d(gps_ts, lats, kind="linear", bounds_error=False, fill_value="extrapolate")
            interp_lon = interp1d(gps_ts, lons, kind="linear", bounds_error=False, fill_value="extrapolate")
            interp_alt = interp1d(gps_ts, alts, kind="linear", bounds_error=False, fill_value="extrapolate")

            lat_eval = interp_lat(frame_timestamps)
            lon_eval = interp_lon(frame_timestamps)
            alt_eval = interp_alt(frame_timestamps)

            for i, f in enumerate(self.frames):
                f.gps = GPSFix(
                    timestamp=float(f.timestamp),
                    latitude=float(lat_eval[i]),
                    longitude=float(lon_eval[i]),
                    altitude_m=float(alt_eval[i]),
                )
                # Compute ENU coordinates
                e, n, u = lla_to_enu(f.gps.latitude, f.gps.longitude, f.gps.altitude_m, *self.origin_lla)
                f.position_enu = (float(e), float(n), float(u))
        else:
            # Explicitly clear position_enu and flag local metric mode
            for f in self.frames:
                f.gps = None
                f.position_enu = None

        # 2. Synchronize IMU
        if len(self.imu_measurements) >= 2:
            imu_ts = np.array([m.timestamp for m in self.imu_measurements], dtype=np.float64)
            accel = np.array([m.accel_xyz for m in self.imu_measurements], dtype=np.float64)
            gyro = np.array([m.gyro_xyz for m in self.imu_measurements], dtype=np.float64)

            interp_accel = interp1d(imu_ts, accel, axis=0, kind="linear", bounds_error=False, fill_value="extrapolate")
            interp_gyro = interp1d(imu_ts, gyro, axis=0, kind="linear", bounds_error=False, fill_value="extrapolate")

            accel_eval = interp_accel(frame_timestamps)
            gyro_eval = interp_gyro(frame_timestamps)

            for i, f in enumerate(self.frames):
                f.imu = IMUMeasurement(
                    timestamp=float(f.timestamp),
                    accel_xyz=(float(accel_eval[i, 0]), float(accel_eval[i, 1]), float(accel_eval[i, 2])),
                    gyro_xyz=(float(gyro_eval[i, 0]), float(gyro_eval[i, 1]), float(gyro_eval[i, 2])),
                )

        # 3. Synchronize Barometer
        if len(self.barometer_measurements) >= 2:
            baro_ts = np.array([b.timestamp for b in self.barometer_measurements], dtype=np.float64)
            press = np.array([b.pressure_hpa for b in self.barometer_measurements], dtype=np.float64)
            baro_alt = np.array([b.altitude_m for b in self.barometer_measurements], dtype=np.float64)

            interp_press = interp1d(baro_ts, press, kind="linear", bounds_error=False, fill_value="extrapolate")
            interp_alt = interp1d(baro_ts, baro_alt, kind="linear", bounds_error=False, fill_value="extrapolate")

            press_eval = interp_press(frame_timestamps)
            alt_eval = interp_alt(frame_timestamps)

            for i, f in enumerate(self.frames):
                f.barometer = BarometerMeasurement(
                    timestamp=float(f.timestamp),
                    pressure_hpa=float(press_eval[i]),
                    altitude_m=float(alt_eval[i]),
                )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FlightSession:
        camera = CameraModel(**d["camera"])
        provenance = ProvenanceMode(d["provenance"])
        frames = [
            FrameMetadata(
                frame_idx=f["frame_idx"],
                timestamp=f["timestamp"],
                image_filename=f["image_filename"],
                gps=GPSFix(**f["gps"]) if f.get("gps") else None,
                imu=IMUMeasurement(**f["imu"]) if f.get("imu") else None,
                barometer=BarometerMeasurement(**f["barometer"]) if f.get("barometer") else None,
                position_enu=tuple(f["position_enu"]) if f.get("position_enu") else None,
            )
            for f in d.get("frames", [])
        ]
        gps_fixes = [GPSFix(**g) for g in d.get("gps_fixes", [])]
        imu_measurements = [IMUMeasurement(**m) for m in d.get("imu_measurements", [])]
        baro_measurements = [BarometerMeasurement(**b) for b in d.get("barometer_measurements", [])]
        origin = tuple(d["origin_lla"]) if d.get("origin_lla") else None

        return cls(
            session_id=d["session_id"],
            provenance=provenance,
            camera=camera,
            frames=frames,
            gps_fixes=gps_fixes,
            imu_measurements=imu_measurements,
            barometer_measurements=baro_measurements,
            origin_lla=origin,
            crs_epsg=d.get("crs_epsg", 4326),
        )

    def save_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_json(cls, path: str | Path) -> FlightSession:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return cls.from_dict(d)
