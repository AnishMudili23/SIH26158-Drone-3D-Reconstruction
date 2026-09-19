"""Regression tests for src/geo/flight_metadata.py's GPS-log interpolation."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from geo.flight_metadata import interpolate_gps_fixes


def _write_log(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp_s", "lat", "lon", "alt_m"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def test_interpolates_linearly_between_fixes(tmp_path):
    log_path = tmp_path / "flight.csv"
    _write_log(log_path, [
        {"timestamp_s": 0.0, "lat": 10.0, "lon": 20.0, "alt_m": 100.0},
        {"timestamp_s": 10.0, "lat": 11.0, "lon": 21.0, "alt_m": 110.0},
    ])

    fixes = interpolate_gps_fixes(["f0.jpg"], [5.0], log_path)
    assert len(fixes) == 1
    assert fixes[0].lat == 10.5
    assert fixes[0].lon == 20.5
    assert fixes[0].alt_m == 105.0


def test_skips_frames_far_outside_log_time_range(tmp_path):
    log_path = tmp_path / "flight.csv"
    _write_log(log_path, [
        {"timestamp_s": 0.0, "lat": 10.0, "lon": 20.0, "alt_m": 100.0},
        {"timestamp_s": 10.0, "lat": 11.0, "lon": 21.0, "alt_m": 110.0},
    ])

    fixes = interpolate_gps_fixes(
        ["f0.jpg", "f1.jpg"], [5.0, 100.0], log_path, max_extrapolation_s=1.0
    )
    assert len(fixes) == 1
    assert fixes[0].frame_name == "f0.jpg"


def test_handles_unsorted_log_rows(tmp_path):
    log_path = tmp_path / "flight.csv"
    _write_log(log_path, [
        {"timestamp_s": 10.0, "lat": 11.0, "lon": 21.0, "alt_m": 110.0},
        {"timestamp_s": 0.0, "lat": 10.0, "lon": 20.0, "alt_m": 100.0},
    ])
    fixes = interpolate_gps_fixes(["f0.jpg"], [5.0], log_path)
    assert fixes[0].lat == 10.5
