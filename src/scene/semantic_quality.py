from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum

import numpy as np


class SemanticQualityTier(str, Enum):
    TRUSTED = "TRUSTED"                        # Multi-view agreement is high and no
                                                # geometrically implausible instances found.
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"  # At least one class-tagged instance has a
                                                # geometrically implausible size — a strong
                                                # domain-shift signal that multi-view voting
                                                # agreement alone cannot catch, since the
                                                # segmentation model can be confidently and
                                                # consistently wrong across every view.
    LOW_CONFIDENCE = "LOW_CONFIDENCE"          # Multi-view voting itself disagrees a lot —
                                                # the segmentation model can't even agree with
                                                # itself across frames.
    UNKNOWN = "UNKNOWN"                        # No per-point voting confidence was computed
                                                # (single-view class tagging fallback path).


@dataclass
class SemanticQualityReport:
    n_points: int
    mean_semantic_confidence: float | None
    low_confidence_point_pct: float | None
    oversized_instance_ids: list[int]
    oversized_instance_count: int
    max_plausible_footprint_m2: float
    quality_tier: SemanticQualityTier
    summary: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["quality_tier"] = self.quality_tier.value
        return d


class SemanticQualityEvaluator:
    """Flags when semantic class tags shouldn't be trusted at face value.

    Multi-view voting agreement (`MultiViewSemanticVoter.semantic_confidences`) only
    detects when cameras *disagree* with each other about a point's class. It cannot
    detect the failure mode found running this pipeline on real out-of-domain terrain
    (a dry reservoir basin misclassified as 65% "Building"): every view agreed, because
    the segmentation model was confidently and consistently wrong, not uncertain. So this
    evaluator adds an independent, orthogonal check — geometric plausibility of the
    class-tagged instances the class feeds into (e.g. a "Building" footprint far larger
    than any real single structure is ever surveyed at) — and combines both signals
    rather than trusting multi-view agreement alone.
    """

    def __init__(
        self,
        low_confidence_threshold: float = 0.3,
        low_confidence_pct_warn: float = 30.0,
        mean_confidence_warn: float = 0.4,
        max_plausible_footprint_m2: float = 2000.0,
    ):
        self.low_confidence_threshold = low_confidence_threshold
        self.low_confidence_pct_warn = low_confidence_pct_warn
        self.mean_confidence_warn = mean_confidence_warn
        self.max_plausible_footprint_m2 = max_plausible_footprint_m2

    def evaluate(
        self,
        semantic_confidences: np.ndarray | None,
        building_instances: list | None,
    ) -> SemanticQualityReport:
        building_instances = building_instances or []
        oversized = [
            b.instance_id for b in building_instances
            if b.footprint_area_m2 > self.max_plausible_footprint_m2
        ]

        if semantic_confidences is None or len(semantic_confidences) == 0:
            mean_conf = None
            low_pct = None
            n_points = 0
        else:
            n_points = int(len(semantic_confidences))
            mean_conf = float(np.mean(semantic_confidences))
            low_pct = float((semantic_confidences < self.low_confidence_threshold).mean() * 100)

        if oversized and (mean_conf is None or mean_conf >= self.mean_confidence_warn):
            tier = SemanticQualityTier.REVIEW_RECOMMENDED
            agreement_note = (
                f"multi-view agreement is high (mean confidence {mean_conf:.2f})"
                if mean_conf is not None else "multi-view agreement was not computed"
            )
            summary = (
                f"{len(oversized)} class-tagged instance(s) exceed the plausible single-structure "
                f"footprint ({self.max_plausible_footprint_m2:.0f} m^2) - instance IDs {oversized}. "
                f"This is a domain-shift red flag: {agreement_note}, which alone would look fine, "
                f"but agreement only means the model is consistent, not correct. Treat semantic "
                f"class tags for this mission as unverified until reviewed against the orthomosaic."
            )
        elif mean_conf is not None and mean_conf < self.mean_confidence_warn:
            tier = SemanticQualityTier.LOW_CONFIDENCE
            summary = (
                f"Mean multi-view semantic agreement is low ({mean_conf:.2f} < {self.mean_confidence_warn}); "
                f"{low_pct:.1f}% of points fall below the per-point confidence floor "
                f"({self.low_confidence_threshold}). Cameras disagree with each other about class "
                f"labels across this scene — class tags should be treated as low confidence."
            )
        elif oversized:
            tier = SemanticQualityTier.REVIEW_RECOMMENDED
            summary = (
                f"{len(oversized)} class-tagged instance(s) exceed the plausible single-structure "
                f"footprint - instance IDs {oversized}. Semantic confidence signal unavailable; "
                f"review against the orthomosaic before trusting class tags."
            )
        elif mean_conf is None:
            tier = SemanticQualityTier.UNKNOWN
            summary = (
                "No multi-view voting confidence available (single-view class tagging fallback "
                "was used). Semantic class tags are unverified."
            )
        else:
            tier = SemanticQualityTier.TRUSTED
            summary = (
                f"Mean multi-view semantic agreement is high ({mean_conf:.2f}) and no class-tagged "
                f"instance exceeds the plausible footprint threshold. Class tags appear trustworthy."
            )

        return SemanticQualityReport(
            n_points=n_points,
            mean_semantic_confidence=round(mean_conf, 4) if mean_conf is not None else None,
            low_confidence_point_pct=round(low_pct, 2) if low_pct is not None else None,
            oversized_instance_ids=oversized,
            oversized_instance_count=len(oversized),
            max_plausible_footprint_m2=self.max_plausible_footprint_m2,
            quality_tier=tier,
            summary=summary,
        )
