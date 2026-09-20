from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from common.alignment import umeyama_alignment


@dataclass
class TrajectoryAccuracyMetrics:
    ate_rmse_m: float
    ate_mean_m: float
    ate_max_m: float
    rpe_translation_rmse_m: float
    rpe_rotation_rmse_deg: float
    num_evaluated_poses: int


def compute_ate_rmse(
    estimated_positions: np.ndarray,
    ground_truth_positions: np.ndarray,
    align_trajectories: bool = True,
) -> tuple[float, float, float]:
    """Computes Absolute Trajectory Error (ATE RMSE, Mean, Max) in meters between estimated and ground truth trajectories.
    
    Args:
        estimated_positions: (N, 3) array
        ground_truth_positions: (N, 3) array
        align_trajectories: If True, uses Umeyama similarity transform to align estimated onto GT first.
    """
    if len(estimated_positions) != len(ground_truth_positions):
        raise ValueError(
            f"Shape mismatch: estimated {estimated_positions.shape} vs ground truth {ground_truth_positions.shape}"
        )
    if len(estimated_positions) < 3:
        return 0.0, 0.0, 0.0

    if align_trajectories:
        scale, rot, trans = umeyama_alignment(estimated_positions, ground_truth_positions)
        aligned = (scale * rot @ estimated_positions.T).T + trans
    else:
        aligned = estimated_positions

    residuals = np.linalg.norm(aligned - ground_truth_positions, axis=1)
    rmse = float(np.sqrt(np.mean(residuals**2)))
    mean_err = float(np.mean(residuals))
    max_err = float(np.max(residuals))
    return rmse, mean_err, max_err


def compute_rpe(
    estimated_positions: np.ndarray,
    ground_truth_positions: np.ndarray,
    step: int = 1,
) -> float:
    """Computes Relative Pose Error (RPE) translation drift in meters per step."""
    if len(estimated_positions) <= step:
        return 0.0

    # Relative displacements
    delta_est = estimated_positions[step:] - estimated_positions[:-step]
    delta_gt = ground_truth_positions[step:] - ground_truth_positions[:-step]

    rpe_residuals = np.linalg.norm(delta_est - delta_gt, axis=1)
    return float(np.sqrt(np.mean(rpe_residuals**2)))
