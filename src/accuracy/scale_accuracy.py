from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class ScaleAccuracyMetrics:
    scale_error_pct: float
    scale_precision_pct: float
    mean_distance_residual_m: float
    max_distance_residual_m: float
    num_distance_checks: int


def compute_scale_accuracy(estimated_scale: float, true_scale: float = 1.0) -> tuple[float, float]:
    """Computes percentage scale error and scale precision."""
    if true_scale <= 0.0:
        raise ValueError(f"true_scale must be positive, got {true_scale}")
    err_pct = float(abs(estimated_scale - true_scale) / true_scale * 100.0)
    precision_pct = float(max(0.0, 100.0 - err_pct))
    return err_pct, precision_pct


def compute_distance_metrics(
    estimated_points_a: np.ndarray,
    estimated_points_b: np.ndarray,
    ground_truth_distances: np.ndarray,
) -> tuple[float, float]:
    """Evaluates pairwise 3D Euclidean distances between known point pairs against ground truth distances.
    
    Args:
        estimated_points_a: (N, 3)
        estimated_points_b: (N, 3)
        ground_truth_distances: (N,)
    """
    est_dists = np.linalg.norm(estimated_points_a - estimated_points_b, axis=1)
    residuals = np.abs(est_dists - ground_truth_distances)
    mean_err = float(np.mean(residuals)) if len(residuals) > 0 else 0.0
    max_err = float(np.max(residuals)) if len(residuals) > 0 else 0.0
    return mean_err, max_err
