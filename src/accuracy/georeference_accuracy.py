from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class GeoreferenceAccuracyMetrics:
    horizontal_rmse_m: float
    vertical_rmse_m: float
    position_3d_rmse_m: float
    max_horizontal_error_m: float
    max_vertical_error_m: float
    num_checkpoints: int


def compute_georeference_accuracy(
    estimated_enu_positions: np.ndarray,
    ground_truth_enu_positions: np.ndarray,
) -> GeoreferenceAccuracyMetrics:
    """Computes horizontal (XY), vertical (Z), and 3D RMSE in meters between estimated ENU positions and surveyed ground truth coordinates."""
    if len(estimated_enu_positions) != len(ground_truth_enu_positions):
        raise ValueError(
            f"Shape mismatch: {estimated_enu_positions.shape} vs {ground_truth_enu_positions.shape}"
        )
    if len(estimated_enu_positions) == 0:
        return GeoreferenceAccuracyMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0)

    diff = estimated_enu_positions - ground_truth_enu_positions
    dx, dy, dz = diff[:, 0], diff[:, 1], diff[:, 2]

    horiz_sq_err = dx**2 + dy**2
    vert_sq_err = dz**2
    total_3d_sq_err = horiz_sq_err + vert_sq_err

    horiz_rmse = float(np.sqrt(np.mean(horiz_sq_err)))
    vert_rmse = float(np.sqrt(np.mean(vert_sq_err)))
    total_3d_rmse = float(np.sqrt(np.mean(total_3d_sq_err)))

    max_horiz = float(np.max(np.sqrt(horiz_sq_err)))
    max_vert = float(np.max(np.abs(dz)))

    return GeoreferenceAccuracyMetrics(
        horizontal_rmse_m=horiz_rmse,
        vertical_rmse_m=vert_rmse,
        position_3d_rmse_m=total_3d_rmse,
        max_horizontal_error_m=max_horiz,
        max_vertical_error_m=max_vert,
        num_checkpoints=len(estimated_enu_positions),
    )
