"""
Phase 3 input bridge — reads a real flight's GPS/telemetry log and produces one GpsFix
per extracted keyframe, by timestamp interpolation.

Format assumed: a CSV with columns `timestamp_s, lat, lon, alt_m` (timestamp relative to
the same t=0 as the video). This is the simplest common denominator most drone
telemetry exports (DJI SRT-derived CSV, ArduPilot/PX4 log exports, etc.) can be
converted to; PRD.md/ARCHITECTURE.md don't mandate a specific vendor format, and
picking one common intermediate format here keeps the rest of the pipeline decoupled
from any specific flight controller's raw log format.

GPS logs are almost never sampled at exactly the video's frame timestamps, so each
frame's position is linearly interpolated between the two nearest GPS fixes — standard
practice for this kind of sensor fusion, and adequate given GPS's own noise floor is
typically larger than the interpolation error over a fraction-of-a-second gap.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from geo.scale_alignment import GpsFix  # noqa: E402


def load_flight_log(csv_path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Returns (timestamps_s, lats, lons, alts_m), sorted by timestamp."""
    timestamps, lats, lons, alts = [], [], [], []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamps.append(float(row["timestamp_s"]))
            lats.append(float(row["lat"]))
            lons.append(float(row["lon"]))
            alts.append(float(row["alt_m"]))

    order = np.argsort(timestamps)
    return (
        np.array(timestamps)[order],
        np.array(lats)[order],
        np.array(lons)[order],
        np.array(alts)[order],
    )


def interpolate_gps_fixes(
    frame_names: list[str],
    frame_timestamps_s: list[float],
    flight_log_csv: str | Path,
    max_extrapolation_s: float = 1.0,
) -> list[GpsFix]:
    """Linear interpolation of the flight log onto each frame's timestamp.

    Frames whose timestamp falls more than `max_extrapolation_s` outside the flight
    log's own time range are skipped (extrapolating GPS position far beyond the last
    known fix is unreliable) rather than silently extrapolated — logged via the
    returned list simply being shorter than `frame_names`.
    """
    log_t, log_lat, log_lon, log_alt = load_flight_log(flight_log_csv)
    t_min, t_max = log_t.min() - max_extrapolation_s, log_t.max() + max_extrapolation_s

    fixes = []
    for name, t in zip(frame_names, frame_timestamps_s):
        if t < t_min or t > t_max:
            continue
        t_clamped = np.clip(t, log_t.min(), log_t.max())
        lat = float(np.interp(t_clamped, log_t, log_lat))
        lon = float(np.interp(t_clamped, log_t, log_lon))
        alt = float(np.interp(t_clamped, log_t, log_alt))
        fixes.append(GpsFix(frame_name=name, lat=lat, lon=lon, alt_m=alt))
    return fixes
