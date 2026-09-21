import numpy as np
from src.scene.building_instances import BuildingInstance
from src.scene.semantic_quality import SemanticQualityEvaluator, SemanticQualityTier


def _instance(instance_id: int, footprint_area_m2: float) -> BuildingInstance:
    return BuildingInstance(
        instance_id=instance_id,
        centroid_xyz=(0.0, 0.0, 0.0),
        footprint_area_m2=footprint_area_m2,
        base_elevation_m=0.0,
        peak_elevation_m=5.0,
        height_m=5.0,
        volume_m3=footprint_area_m2 * 5.0,
        point_count=1000,
        mean_confidence=0.7,
        bounding_box_min=(0.0, 0.0, 0.0),
        bounding_box_max=(1.0, 1.0, 1.0),
    )


def test_no_semantic_confidence_no_instances_is_unknown():
    evaluator = SemanticQualityEvaluator()
    rep = evaluator.evaluate(None, [])
    assert rep.quality_tier == SemanticQualityTier.UNKNOWN
    assert rep.mean_semantic_confidence is None
    assert rep.oversized_instance_count == 0


def test_high_agreement_no_oversized_is_trusted():
    evaluator = SemanticQualityEvaluator()
    conf = np.full(1000, 0.9)
    rep = evaluator.evaluate(conf, [_instance(1, 100.0), _instance(2, 300.0)])
    assert rep.quality_tier == SemanticQualityTier.TRUSTED
    assert rep.oversized_instance_count == 0


def test_low_agreement_flags_low_confidence():
    evaluator = SemanticQualityEvaluator()
    conf = np.full(1000, 0.1)
    rep = evaluator.evaluate(conf, [_instance(1, 100.0)])
    assert rep.quality_tier == SemanticQualityTier.LOW_CONFIDENCE
    assert rep.mean_semantic_confidence < 0.4


def test_oversized_instance_with_high_agreement_flags_review_recommended():
    # This is the exact failure mode found on real data: every camera view agrees
    # (high semantic_confidences) but the class label is still wrong, because the
    # segmentation model is confidently and consistently out-of-domain. Multi-view
    # agreement alone would call this TRUSTED — the size check must catch it instead.
    evaluator = SemanticQualityEvaluator(max_plausible_footprint_m2=2000.0)
    conf = np.full(1000, 0.9)
    rep = evaluator.evaluate(conf, [_instance(1, 9049.67), _instance(2, 300.0)])
    assert rep.quality_tier == SemanticQualityTier.REVIEW_RECOMMENDED
    assert rep.oversized_instance_ids == [1]
    assert rep.oversized_instance_count == 1


def test_oversized_instance_without_confidence_still_flags_review_recommended():
    evaluator = SemanticQualityEvaluator(max_plausible_footprint_m2=2000.0)
    rep = evaluator.evaluate(None, [_instance(1, 9049.67)])
    assert rep.quality_tier == SemanticQualityTier.REVIEW_RECOMMENDED
    assert rep.oversized_instance_ids == [1]
