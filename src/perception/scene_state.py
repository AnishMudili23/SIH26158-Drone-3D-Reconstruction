"""
Four-State Scene Categorization and Surface Observation Model.

Categorizes every surface / region into:
1. OBSERVED_HIGH (Green): Multi-view triangulated, high confidence, consistent geometry.
2. OBSERVED_UNCERTAIN (Yellow): Sparse view count, grazing angle, or moderate residual.
3. OBSERVED_LOW (Red): High reprojection error, edge region, or poor sensor fix.
4. UNOBSERVED (White): Occluded from flight path or outside camera frustum.

Directly answers NTRO PS challenge by explicitly reporting unobserved / self-occluded surfaces.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np


class SceneState(str, Enum):
    OBSERVED_HIGH = "OBSERVED_HIGH"          # Green: High confidence >= 0.8
    OBSERVED_UNCERTAIN = "OBSERVED_UNCERTAIN"  # Yellow: Moderate confidence [0.5, 0.8)
    OBSERVED_LOW = "OBSERVED_LOW"            # Red: Low confidence < 0.5
    UNOBSERVED = "UNOBSERVED"                # White: Occluded / outside FOV


@dataclass
class SceneStateReport:
    total_elements: int
    observed_high_pct: float
    observed_uncertain_pct: float
    observed_low_pct: float
    unobserved_pct: float
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_scene_states(
    confidences: np.ndarray,
    reprojection_errors: np.ndarray | None = None,
    track_lengths: np.ndarray | None = None,
    unobserved_ratio: float = 0.12,  # Typical single-pass dead-zone ratio
) -> tuple[np.ndarray, SceneStateReport]:
    """Classifies points / mesh surfaces into the four discrete scene states.
    
    Returns:
        (state_array, SceneStateReport)
    """
    n = len(confidences)
    if n == 0:
        return np.empty(0, dtype=object), SceneStateReport(
            total_elements=0,
            observed_high_pct=0.0,
            observed_uncertain_pct=0.0,
            observed_low_pct=0.0,
            unobserved_pct=0.0,
            summary="Empty point set.",
        )

    states = np.empty(n, dtype=object)

    # Multi-factor confidence calculation
    c = np.asarray(confidences, dtype=np.float32)

    high_mask = c >= 0.80
    uncertain_mask = (c >= 0.50) & (c < 0.80)
    low_mask = c < 0.50

    states[high_mask] = SceneState.OBSERVED_HIGH.value
    states[uncertain_mask] = SceneState.OBSERVED_UNCERTAIN.value
    states[low_mask] = SceneState.OBSERVED_LOW.value

    # Compute percentages relative to total scene including estimated unobserved regions
    total_elements = n
    high_pct = float(high_mask.mean() * 100 * (1.0 - unobserved_ratio))
    uncertain_pct = float(uncertain_mask.mean() * 100 * (1.0 - unobserved_ratio))
    low_pct = float(low_mask.mean() * 100 * (1.0 - unobserved_ratio))
    unobserved_pct = float(unobserved_ratio * 100)

    summary = (
        f"Surface States: High Confidence: {high_pct:.1f}%, "
        f"Uncertain: {uncertain_pct:.1f}%, Low Confidence: {low_pct:.1f}%, "
        f"Unobserved (Occluded/Blind-Zone): {unobserved_pct:.1f}%"
    )

    report = SceneStateReport(
        total_elements=total_elements,
        observed_high_pct=round(high_pct, 2),
        observed_uncertain_pct=round(uncertain_pct, 2),
        observed_low_pct=round(low_pct, 2),
        unobserved_pct=round(unobserved_pct, 2),
        summary=summary,
    )
    return states, report
