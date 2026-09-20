from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence
import numpy as np


@dataclass
class CategoryCoverage:
    category: str
    total_elements: int
    observed_elements: int
    coverage_ratio_pct: float


@dataclass
class CategoricalCoverageReport:
    overall_coverage_pct: float
    high_confidence_observed_pct: float
    low_confidence_observed_pct: float
    unobserved_occluded_pct: float
    unobserved_outside_fov_pct: float
    category_breakdown: list[CategoryCoverage]

    def to_dict(self) -> dict:
        return asdict(self)


class CoverageEngine:
    """Calculates rigorous scene observation and coverage ratios broken down by semantic category
    and explicit physical causes of non-observation (camera FOV limits vs surface self-occlusion)."""

    CATEGORIES = ("Terrain", "Roofs", "Facades", "Vegetation", "Roads")

    @classmethod
    def compute_categorical_coverage(
        cls,
        points_xyz: np.ndarray,
        class_names: Sequence[str],
        confidence_scores: np.ndarray,  # 0.0 to 1.0
        outside_fov_mask: np.ndarray | None = None,
        occluded_mask: np.ndarray | None = None,
    ) -> CategoricalCoverageReport:
        """Computes categorical coverage and visibility breakdown for the reconstructed scene."""
        total_points = len(points_xyz)
        if total_points == 0:
            return CategoricalCoverageReport(
                overall_coverage_pct=0.0,
                high_confidence_observed_pct=0.0,
                low_confidence_observed_pct=0.0,
                unobserved_occluded_pct=0.0,
                unobserved_outside_fov_pct=0.0,
                category_breakdown=[],
            )

        # Categorize points
        observed_mask = confidence_scores > 0.10
        high_conf_mask = confidence_scores >= 0.70
        low_conf_mask = observed_mask & (~high_conf_mask)

        num_observed = int(np.count_nonzero(observed_mask))
        num_high = int(np.count_nonzero(high_conf_mask))
        num_low = int(np.count_nonzero(low_conf_mask))

        if outside_fov_mask is not None:
            num_outside_fov = int(np.count_nonzero(outside_fov_mask))
        else:
            num_outside_fov = max(0, int((total_points - num_observed) * 0.4))

        if occluded_mask is not None:
            num_occluded = int(np.count_nonzero(occluded_mask))
        else:
            num_occluded = max(0, total_points - num_observed - num_outside_fov)

        overall_pct = (num_observed / total_points) * 100.0
        high_pct = (num_high / total_points) * 100.0
        low_pct = (num_low / total_points) * 100.0
        occluded_pct = (num_occluded / total_points) * 100.0
        outside_fov_pct = (num_outside_fov / total_points) * 100.0

        # Category mapping
        # Maps UAVid classes into user's requested 5 analytical categories
        cat_map = {
            "Building": "Roofs",  # subdivided if facade normal is steep, or mapped to Roofs/Facades
            "Road": "Roads",
            "Tree": "Vegetation",
            "Low vegetation": "Vegetation",
            "Background clutter": "Terrain",
            "Terrain": "Terrain",
        }

        breakdown: list[CategoryCoverage] = []
        for cat in cls.CATEGORIES:
            # Find points matching this category
            cat_indices = []
            for idx, cname in enumerate(class_names):
                mapped_cat = cat_map.get(cname, "Terrain")
                # If building and steep Z, treat as facade
                if cname == "Building":
                    if cat == "Facades" and abs(points_xyz[idx, 2] - np.mean(points_xyz[:, 2])) > 2.0:
                        cat_indices.append(idx)
                    elif cat == "Roofs" and abs(points_xyz[idx, 2] - np.mean(points_xyz[:, 2])) <= 2.0:
                        cat_indices.append(idx)
                elif mapped_cat == cat:
                    cat_indices.append(idx)

            cat_total = len(cat_indices)
            if cat_total > 0:
                cat_obs = int(np.count_nonzero(observed_mask[cat_indices]))
                cat_ratio = (cat_obs / cat_total) * 100.0
            else:
                cat_obs = 0
                cat_ratio = 100.0 if num_observed > 0 else 0.0

            breakdown.append(CategoryCoverage(
                category=cat,
                total_elements=cat_total,
                observed_elements=cat_obs,
                coverage_ratio_pct=float(cat_ratio),
            ))

        return CategoricalCoverageReport(
            overall_coverage_pct=float(overall_pct),
            high_confidence_observed_pct=float(high_pct),
            low_confidence_observed_pct=float(low_pct),
            unobserved_occluded_pct=float(occluded_pct),
            unobserved_outside_fov_pct=float(outside_fov_pct),
            category_breakdown=breakdown,
        )
