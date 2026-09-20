"""Adapter for the Zurich Urban MAV dataset (RPG, ETH Zurich / UZH) — real UAV video,
GPS, IMU, barometer, camera calibration, and surveyed ground-truth positions.

Source: https://rpg.ifi.uzh.ch/zurichmavdataset.html (AGZ_subset.zip, CC-licensed,
direct download, no registration). Verified against the real downloaded subset
(350 images, ~18.6s segment) in this project's own investigation — see PROGRESS.md.

Real, dataset-specific facts baked into this parser (verified directly against the
files, not assumed):
  - `MAV Images/{imgid:05d}.jpg` <-> `Log Files/OnboardGPS.csv` row where
    `imgid` column matches the zero-padded filename number. Verified via EXIF GPS
    tag on 00001.jpg matching OnboardGPS.csv's imgid=1 row to 1e-7 deg.
  - CSV headers have leading spaces and trailing empty columns (raw MATLAB-export
    format) — every column is looked up by stripped name, not by fixed position.
  - `Timpstemp` (sic — dataset's own typo, kept verbatim as the source column name)
    is in microseconds since an arbitrary onboard clock epoch, not Unix time.
  - `Log Files/GroundTruthAGL.csv` gives surveyed ground-truth camera positions in a
    projected UTM-like CRS (UTM zone 32N, matching Zurich's location) for a sparse
    subset of imgids across the *full* 81,169-image flight — only the rows whose
    imgid falls inside this subset's 1..350 range are usable checkpoints here.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from telemetry.flight_session import (  # noqa: E402
    BarometerMeasurement,
    CameraModel,
    FlightSession,
    FrameMetadata,
    GPSFix,
    IMUMeasurement,
    ProvenanceMode,
)

_MICROSECONDS_PER_SECOND = 1_000_000.0


@dataclass
class GroundTruthCheckpoint:
    """A surveyed camera position for one frame, in UTM meters (not the FlightSession's
    own ENU frame — caller must reproject before comparing to reconstruction output)."""
    image_filename: str
    utm_x: float
    utm_y: float
    utm_z: float
    utm_zone_epsg: int = 32632  # UTM zone 32N (Zurich, Switzerland)


def _read_csv_by_header(path: Path) -> tuple[list[str], list[list[str]]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    return header, rows


def _col(header: list[str], name: str) -> int:
    return header.index(name)


def load_zurich_mav_session(dataset_dir: str | Path) -> tuple[FlightSession, list[Path], list[GroundTruthCheckpoint]]:
    """Parses an extracted `AGZ_subset/` directory into a FlightSession.

    Returns
    -------
    (session, image_paths, gt_checkpoints)
        `image_paths[i]` corresponds to `session.frames[i]`, ordered by frame_idx.
        `gt_checkpoints` holds only the frames that have a surveyed ground-truth
        position (a sparse subset — real datasets rarely survey every frame).
    """
    dataset_dir = Path(dataset_dir)
    images_dir = dataset_dir / "MAV Images"
    log_dir = dataset_dir / "Log Files"
    calib_path = dataset_dir / "calibration_data.npz"

    if not images_dir.is_dir():
        raise FileNotFoundError(f"Expected 'MAV Images' directory under {dataset_dir}")

    # --- Camera calibration ---
    calib = np.load(calib_path)
    k = calib["intrinsic_matrix"]
    dist = calib["distCoeff"].reshape(-1)  # (k1, k2, p1, p2, k3), OpenCV order
    sample_img_path = sorted(images_dir.glob("*.jpg"))[0]
    import cv2
    sample_img = cv2.imread(str(sample_img_path))
    height, width = sample_img.shape[:2]
    camera = CameraModel(
        width=width,
        height=height,
        fx=float(k[0, 0]),
        fy=float(k[1, 1]),
        cx=float(k[0, 2]),
        cy=float(k[1, 2]),
        distortion_coeffs=tuple(float(c) for c in dist),
        model_type="OPENCV",
    )

    # --- Frame list + per-frame timestamp from OnboardGPS's own imgid/Timpstemp columns ---
    image_paths = sorted(images_dir.glob("*.jpg"))
    header, gps_rows = _read_csv_by_header(log_dir / "OnboardGPS.csv")
    ts_col, imgid_col = _col(header, "Timpstemp"), _col(header, "imgid")
    lat_col, lon_col, alt_col = _col(header, "lat"), _col(header, "lon"), _col(header, "alt")

    gps_by_imgid: dict[int, tuple[float, float, float, float]] = {}
    for row in gps_rows:
        imgid = int(row[imgid_col])
        gps_by_imgid[imgid] = (
            float(row[ts_col]) / _MICROSECONDS_PER_SECOND,
            float(row[lat_col]),
            float(row[lon_col]),
            float(row[alt_col]),
        )

    frames: list[FrameMetadata] = []
    kept_image_paths: list[Path] = []
    for idx, img_path in enumerate(image_paths):
        imgid = int(img_path.stem)
        if imgid not in gps_by_imgid:
            continue  # this frame's telemetry row is missing — skip rather than guess
        ts, _, _, _ = gps_by_imgid[imgid]
        frames.append(FrameMetadata(frame_idx=len(frames), timestamp=ts, image_filename=img_path.name))
        kept_image_paths.append(img_path)

    # --- Full-resolution GPS fix list (used for interpolation, same source as above) ---
    gps_fixes = [
        GPSFix(timestamp=ts, latitude=lat, longitude=lon, altitude_m=alt)
        for ts, lat, lon, alt in gps_by_imgid.values()
    ]
    gps_fixes.sort(key=lambda g: g.timestamp)

    # --- IMU: RawAccel + RawGyro are logged independently; align gyro onto accel's
    # own timestamps via linear interpolation before building combined measurements ---
    imu_measurements: list[IMUMeasurement] = []
    accel_path, gyro_path = log_dir / "RawAccel.csv", log_dir / "RawGyro.csv"
    if accel_path.exists() and gyro_path.exists():
        a_header, a_rows = _read_csv_by_header(accel_path)
        g_header, g_rows = _read_csv_by_header(gyro_path)
        a_ts_col = _col(a_header, "Timpstemp")
        a_xc, a_yc, a_zc = _col(a_header, "x"), _col(a_header, "y"), _col(a_header, "z")
        g_ts_col = _col(g_header, "Timpstemp")
        g_xc, g_yc, g_zc = _col(g_header, "x"), _col(g_header, "y"), _col(g_header, "z")

        a_ts = np.array([float(r[a_ts_col]) for r in a_rows]) / _MICROSECONDS_PER_SECOND
        a_xyz = np.array([[float(r[a_xc]), float(r[a_yc]), float(r[a_zc])] for r in a_rows])
        g_ts = np.array([float(r[g_ts_col]) for r in g_rows]) / _MICROSECONDS_PER_SECOND
        g_xyz = np.array([[float(r[g_xc]), float(r[g_yc]), float(r[g_zc])] for r in g_rows])

        gx = np.interp(a_ts, g_ts, g_xyz[:, 0])
        gy = np.interp(a_ts, g_ts, g_xyz[:, 1])
        gz = np.interp(a_ts, g_ts, g_xyz[:, 2])

        imu_measurements = [
            IMUMeasurement(
                timestamp=float(a_ts[i]),
                accel_xyz=(float(a_xyz[i, 0]), float(a_xyz[i, 1]), float(a_xyz[i, 2])),
                gyro_xyz=(float(gx[i]), float(gy[i]), float(gz[i])),
            )
            for i in range(len(a_ts))
        ]

    # --- Barometer ---
    baro_measurements: list[BarometerMeasurement] = []
    baro_path = log_dir / "BarometricPressure.csv"
    if baro_path.exists():
        b_header, b_rows = _read_csv_by_header(baro_path)
        b_ts_col = _col(b_header, "Timpstemp")
        b_press_col, b_alt_col = _col(b_header, "Pressure"), _col(b_header, "Altitude")
        baro_measurements = [
            BarometerMeasurement(
                timestamp=float(r[b_ts_col]) / _MICROSECONDS_PER_SECOND,
                pressure_hpa=float(r[b_press_col]),
                altitude_m=float(r[b_alt_col]),
            )
            for r in b_rows
        ]

    session = FlightSession(
        session_id=f"zurich_mav_{dataset_dir.name}",
        provenance=ProvenanceMode.REAL,
        camera=camera,
        frames=frames,
        gps_fixes=gps_fixes,
        imu_measurements=imu_measurements,
        barometer_measurements=baro_measurements,
    )
    session.synchronize_telemetry()

    # --- Ground truth checkpoints (sparse — only imgids that were actually surveyed) ---
    gt_checkpoints: list[GroundTruthCheckpoint] = []
    gt_path = log_dir / "GroundTruthAGL.csv"
    if gt_path.exists():
        kept_imgids = {int(p.stem) for p in kept_image_paths}
        gt_header, gt_rows = _read_csv_by_header(gt_path)
        gid_col = _col(gt_header, "imgid")
        x_col, y_col, z_col = _col(gt_header, "x_gt"), _col(gt_header, "y_gt"), _col(gt_header, "z_gt")
        for row in gt_rows:
            imgid = int(float(row[gid_col]))
            if imgid in kept_imgids:
                gt_checkpoints.append(GroundTruthCheckpoint(
                    image_filename=f"{imgid:05d}.jpg",
                    utm_x=float(row[x_col]), utm_y=float(row[y_col]), utm_z=float(row[z_col]),
                ))

    return session, kept_image_paths, gt_checkpoints
