from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import numpy as np
import open3d as o3d
from scipy.spatial import ConvexHull, QhullError

from src.frame_processing.segmentation import UAVID_CLASS_TO_ID

BUILDING_CLASS_ID = UAVID_CLASS_TO_ID["Building"]


@dataclass
class BuildingInstance:
    instance_id: int
    centroid_xyz: tuple[float, float, float]
    footprint_area_m2: float
    base_elevation_m: float
    peak_elevation_m: float
    height_m: float
    volume_m3: float
    point_count: int
    mean_confidence: float
    bounding_box_min: tuple[float, float, float]
    bounding_box_max: tuple[float, float, float]

    def to_dict(self) -> dict:
        return asdict(self)


class BuildingInstanceExtractor:
    """Extracts discrete building entities from building-tagged 3D points using
    spatial DBSCAN clustering, computing real footprint areas, heights, and volumes."""

    def __init__(
        self,
        dbscan_eps: float = 3.0,
        dbscan_min_points: int = 20,
    ):
        self.eps = dbscan_eps
        self.min_points = dbscan_min_points

    def extract_instances(
        self,
        points_xyz: np.ndarray,
        class_ids: np.ndarray,
        confidences: np.ndarray | None = None,
    ) -> list[BuildingInstance]:
        if len(points_xyz) == 0:
            return []

        bldg_mask = class_ids == BUILDING_CLASS_ID
        bldg_pts = points_xyz[bldg_mask]

        if len(bldg_pts) < self.min_points:
            return []

        bldg_confs = confidences[bldg_mask] if confidences is not None else np.full(len(bldg_pts), 0.85)

        # Open3D native C++ DBSCAN clustering
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(bldg_pts)
        labels = np.array(pcd.cluster_dbscan(eps=self.eps, min_points=self.min_points, print_progress=False))

        instances: list[BuildingInstance] = []
        unique_labels = [l for l in np.unique(labels) if l >= 0]

        for cluster_id in unique_labels:
            mask = labels == cluster_id
            pts = bldg_pts[mask]
            confs = bldg_confs[mask]
            n_pts = len(pts)

            if n_pts < self.min_points:
                continue

            centroid = tuple(np.round(np.mean(pts, axis=0), 3).tolist())
            bb_min = tuple(np.round(np.min(pts, axis=0), 3).tolist())
            bb_max = tuple(np.round(np.max(pts, axis=0), 3).tolist())

            # Base and peak elevation (using percentiles to resist outliers)
            z_vals = pts[:, 2]
            base_z = float(np.percentile(z_vals, 5))
            peak_z = float(np.percentile(z_vals, 95))
            height = float(max(0.1, peak_z - base_z))

            # Footprint area via 2D Convex Hull
            pts_2d = pts[:, :2]
            try:
                if len(np.unique(pts_2d, axis=0)) >= 3:
                    hull = ConvexHull(pts_2d)
                    footprint_area = float(hull.volume)  # in 2D, hull.volume is area
                else:
                    footprint_area = 1.0
            except QhullError:
                # Collinear fallback: bounding box area
                dx = max(0.5, bb_max[0] - bb_min[0])
                dy = max(0.5, bb_max[1] - bb_min[1])
                footprint_area = float(dx * dy)

            # Volumetric estimate: footprint area * height * prism fill factor (0.85 accounts for pitched roof / facets)
            volume = float(footprint_area * height * 0.85)

            instances.append(
                BuildingInstance(
                    instance_id=int(cluster_id) + 1,
                    centroid_xyz=centroid,
                    footprint_area_m2=round(footprint_area, 2),
                    base_elevation_m=round(base_z, 2),
                    peak_elevation_m=round(peak_z, 2),
                    height_m=round(height, 2),
                    volume_m3=round(volume, 2),
                    point_count=n_pts,
                    mean_confidence=round(float(np.mean(confs)), 3),
                    bounding_box_min=bb_min,
                    bounding_box_max=bb_max,
                )
            )

        return instances

    def save_instances_json(self, instances: list[BuildingInstance], output_path: str | Path) -> None:
        data = [inst.to_dict() for inst in instances]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"total_buildings": len(instances), "buildings": data}, f, indent=2)
