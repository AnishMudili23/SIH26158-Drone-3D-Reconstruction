"""Adapter for the UZH-FPV drone racing dataset (RPG, UZH) — real high-speed FPV
footage + IMU, no GPS.

Source: https://fpv.ifi.uzh.ch/datasets/ (race_N.zip, CC BY-NC-SA 3.0, direct download,
no registration). Verified against the real downloaded "race_3" sequence (SplitS
outdoor track) in this project's own investigation — see PROGRESS.md.

Unlike Zurich Urban MAV, this sequence genuinely has no GPS and no surveyed ground
truth (UZH-FPV's Leica laser-tracker ground truth exists only for its indoor
motion-capture sequences, not the outdoor SplitS races) — so `load_uzh_fpv_session`
always produces a FlightSession with an empty `gps_fixes` list and
`ProvenanceMode.REAL` (it IS real hardware data, just without a position sensor).
This exercises FlightSession's `is_georeferenced == False` / LOCAL_METRIC path
against genuine hardware logs, not a synthetic stand-in.

The camera is a fisheye lens (`distortion_model: equidistant`, 4 coefficients),
different from Zurich MAV's OpenCV radial-tangential model — `CameraModel.model_type`
is recorded as "EQUIDISTANT" so callers (e.g. undistortion) know not to treat the
four distortion coefficients as an OpenCV k1,k2,p1,p2 tuple.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from telemetry.flight_session import (  # noqa: E402
    CameraModel,
    FlightSession,
    FrameMetadata,
    IMUMeasurement,
    ProvenanceMode,
)


def load_uzh_fpv_session(dataset_dir: str | Path, calib_dir: str | Path) -> tuple[FlightSession, list[Path]]:
    """Parses an extracted UZH-FPV race sequence directory into a FlightSession.

    Parameters
    ----------
    dataset_dir : directory containing `img/`, `right_images.txt`, `imu.txt`
        (a single extracted `race_N.zip`).
    calib_dir : directory containing `camchain-imucam-race.yaml`
        (the extracted `race_calibration.zip`).

    Returns
    -------
    (session, image_paths) — `image_paths[i]` corresponds to `session.frames[i]`.
    """
    dataset_dir = Path(dataset_dir)
    calib_dir = Path(calib_dir)
    images_dir = dataset_dir / "img"

    with open(calib_dir / "camchain-imucam-race.yaml", "r") as f:
        camchain = yaml.safe_load(f)
    cam0 = camchain["cam0"]
    fx, fy, cx, cy = cam0["intrinsics"]
    width, height = cam0["resolution"]
    camera = CameraModel(
        width=int(width), height=int(height), fx=float(fx), fy=float(fy), cx=float(cx), cy=float(cy),
        distortion_coeffs=tuple(float(c) for c in cam0["distortion_coeffs"]),
        model_type="EQUIDISTANT",
    )

    frames: list[FrameMetadata] = []
    image_paths: list[Path] = []
    with open(dataset_dir / "right_images.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            _id, ts, image_name = parts[0], float(parts[1]), parts[2]
            img_path = images_dir / image_name
            if not img_path.exists():
                continue
            frames.append(FrameMetadata(frame_idx=len(frames), timestamp=ts, image_filename=image_name))
            image_paths.append(img_path)

    imu_measurements: list[IMUMeasurement] = []
    with open(dataset_dir / "imu.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ts, wx, wy, wz, ax, ay, az = (float(x) for x in line.split())
            imu_measurements.append(IMUMeasurement(timestamp=ts, accel_xyz=(ax, ay, az), gyro_xyz=(wx, wy, wz)))

    # Genuinely no GPS in this sequence — REAL provenance (real hardware), empty
    # gps_fixes (not simulated). synchronize_telemetry() will correctly leave every
    # frame's position_enu as None per Phase A's no-fake-GPS rule.
    session = FlightSession(
        session_id=f"uzh_fpv_{dataset_dir.name}",
        provenance=ProvenanceMode.REAL,
        camera=camera,
        frames=frames,
        gps_fixes=[],
        imu_measurements=imu_measurements,
        barometer_measurements=[],
    )
    session.synchronize_telemetry()
    return session, image_paths
