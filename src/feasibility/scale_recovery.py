"""
Phase 0 — Synthetic GPS-noise scale-recovery test.

Monocular SfM (COLMAP without GCPs) recovers structure and camera motion up to an
unknown, arbitrary scale factor. We recover real-world (metric) scale by aligning the
SfM camera-center trajectory (arbitrary units) to the GPS-derived camera-center
trajectory (ENU meters, from flight metadata), using a similarity (7-DoF: scale +
rotation + translation) alignment — the Umeyama method.

This script quantifies: given realistic civilian-GPS noise (and optionally
barometric-altitude noise), how much error should we expect in the recovered scale
factor, as a function of GPS noise level and flight path geometry (path length,
number of camera positions)? This is the number ARCHITECTURE.md's
"Scale + Geo Alignment" stage depends on, and PRD.md Section 5's "~5% scale error"
target is validated against here, synthetically, ahead of any real flight data.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from common.alignment import umeyama_alignment  # noqa: E402


def make_synthetic_flight_path(
    n_points: int,
    path_length_m: float,
    altitude_m: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """A single continuous lawnmower-ish trajectory (gentle S-curve), in ENU meters.

    Ground truth camera centers — this is what COLMAP recovers up to unknown scale,
    and what GPS attempts to measure (with noise).
    """
    t = np.linspace(0, 1, n_points)
    x = t * path_length_m
    y = 15.0 * np.sin(2 * np.pi * t * 2) + rng.normal(0, 0.5, n_points)  # gentle sweep
    z = altitude_m + rng.normal(0, 0.3, n_points)  # small natural altitude variation
    return np.stack([x, y, z], axis=1)


@dataclass
class ScaleTrialResult:
    gps_noise_std_m: float
    n_camera_positions: int
    path_length_m: float
    mean_abs_scale_error_pct: float
    p90_scale_error_pct: float
    n_trials: int


def run_scale_trial(
    gps_noise_std_m: float,
    n_camera_positions: int,
    path_length_m: float,
    altitude_m: float,
    n_trials: int,
    sfm_noise_frac: float,
    seed: int,
) -> ScaleTrialResult:
    """Monte-Carlo over `n_trials` synthetic flights for one (noise, geometry) setting."""
    rng = np.random.default_rng(seed)
    errors_pct = []

    for trial in range(n_trials):
        true_positions = make_synthetic_flight_path(
            n_camera_positions, path_length_m, altitude_m, rng
        )

        # SfM reconstruction: correct shape, unknown scale, small internal noise
        # (COLMAP's own reprojection-driven consistency, not GPS-related).
        true_scale = rng.uniform(0.3, 3.0)  # arbitrary SfM world units per meter
        sfm_positions = true_scale * true_positions
        sfm_positions += rng.normal(0, sfm_noise_frac * path_length_m, sfm_positions.shape)

        # GPS measurement: real-world meters + civilian GPS noise (horizontal + vertical).
        gps_positions = true_positions.copy()
        gps_positions[:, :2] += rng.normal(0, gps_noise_std_m, (n_camera_positions, 2))
        gps_positions[:, 2] += rng.normal(0, gps_noise_std_m * 1.5, n_camera_positions)  # baro/GPS-Z noisier

        recovered_scale, _, _ = umeyama_alignment(sfm_positions, gps_positions)

        # We want the scale that converts SfM units -> meters, i.e. 1/true_scale ground truth.
        true_units_to_meters = 1.0 / true_scale
        error_pct = abs(recovered_scale - true_units_to_meters) / true_units_to_meters * 100.0
        errors_pct.append(error_pct)

    errors_pct = np.array(errors_pct)
    return ScaleTrialResult(
        gps_noise_std_m=gps_noise_std_m,
        n_camera_positions=n_camera_positions,
        path_length_m=path_length_m,
        mean_abs_scale_error_pct=float(errors_pct.mean()),
        p90_scale_error_pct=float(np.percentile(errors_pct, 90)),
        n_trials=n_trials,
    )


def run_full_sweep() -> list[ScaleTrialResult]:
    """Sweep realistic GPS noise levels and flight geometries.

    Noise levels (1-sigma horizontal):
      - 1.0m: RTK/PPK-corrected GPS (optional per PRD.md Section 2)
      - 2.5m: typical consumer drone GPS (DJI-class, no RTK) — our primary target case
      - 5.0m: degraded GPS (urban canyon / weak satellite lock)
    """
    results = []
    noise_levels = [1.0, 2.5, 5.0]
    frame_counts = [50, 150, 400]  # sparse to dense keyframe sets (post Phase-1 filtering)
    path_length_m = 300.0
    altitude_m = 80.0

    for noise in noise_levels:
        for n_frames in frame_counts:
            results.append(
                run_scale_trial(
                    gps_noise_std_m=noise,
                    n_camera_positions=n_frames,
                    path_length_m=path_length_m,
                    altitude_m=altitude_m,
                    n_trials=200,
                    sfm_noise_frac=0.002,  # COLMAP is typically sub-1% internally consistent
                    seed=42,
                )
            )
    return results


if __name__ == "__main__":
    results = run_full_sweep()
    print(json.dumps([asdict(r) for r in results], indent=2))
