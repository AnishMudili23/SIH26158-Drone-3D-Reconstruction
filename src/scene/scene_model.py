from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import numpy as np

from src.scene.building_instances import BuildingInstance


@dataclass
class SceneModel:
    """Unified container representing the complete sensor-fused 3D scene,
    including geometry, multi-view semantics, uncertainty tiers, building instances,
    and georeference metadata."""

    points_xyz: np.ndarray
    points_rgb: np.ndarray
    class_ids: np.ndarray
    geometry_confidence: np.ndarray
    confidence_tiers: list[str]
    class_probabilities: np.ndarray | None = None
    semantic_confidence: np.ndarray | None = None
    observation_counts: np.ndarray | None = None
    camera_poses: list[dict] = field(default_factory=list)
    trajectory_enu: np.ndarray | None = None
    origin_lla: tuple[float, float, float] | None = None
    crs_epsg: int | None = None
    building_instances: list[BuildingInstance] = field(default_factory=list)
    coverage_summary: dict[str, Any] | None = None
    sensor_quality: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def num_points(self) -> int:
        return len(self.points_xyz)

    @property
    def num_buildings(self) -> int:
        return len(self.building_instances)

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "num_points": self.num_points,
            "num_buildings": self.num_buildings,
            "num_cameras": len(self.camera_poses),
            "origin_lla": self.origin_lla,
            "crs_epsg": self.crs_epsg,
            "has_semantics": self.class_probabilities is not None,
            "has_sensor_quality": self.sensor_quality is not None,
            "buildings": [b.to_dict() for b in self.building_instances],
            "metadata": self.metadata,
        }
