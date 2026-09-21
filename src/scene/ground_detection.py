from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import open3d as o3d

from src.frame_processing.segmentation import UAVID_CLASS_TO_ID

# Classes that are definitely elevated obstacles, not bare ground
ELEVATED_CLASS_NAMES = {"Building", "Tree", "Moving car", "Human"}
ELEVATED_CLASS_IDS = {UAVID_CLASS_TO_ID[name] for name in ELEVATED_CLASS_NAMES if name in UAVID_CLASS_TO_ID}


@dataclass
class GroundDetectionResult:
    ground_mask: np.ndarray          # (N,) bool: True for confirmed terrain points
    ground_points_xyz: np.ndarray    # (M, 3) points belonging to terrain surface
    n_ground_points: int
    n_rejected_semantic: int
    n_rejected_vertical: int
    n_rejected_elevated: int


class MorphologicalGroundDetector:
    """Rigorous ground candidate detection combining semantic exclusion,
    surface normal orientation, and morphological minimum-elevation spatial binning."""

    def __init__(
        self,
        grid_cell_size_m: float = 1.0,
        height_threshold_m: float = 0.35,
        min_vertical_normal_nz: float = 0.70,
        knn_normals: int = 15,
    ):
        self.grid_cell_size = grid_cell_size_m
        self.height_thresh = height_threshold_m
        self.min_nz = min_vertical_normal_nz
        self.knn_normals = knn_normals

    def detect_ground(
        self,
        points_xyz: np.ndarray,
        class_ids: np.ndarray | None = None,
    ) -> GroundDetectionResult:
        n_points = len(points_xyz)
        if n_points == 0:
            return GroundDetectionResult(
                ground_mask=np.zeros(0, dtype=bool),
                ground_points_xyz=np.zeros((0, 3), dtype=np.float64),
                n_ground_points=0,
                n_rejected_semantic=0,
                n_rejected_vertical=0,
                n_rejected_elevated=0,
            )

        # 1. Semantic filtering (reject buildings, trees, humans, moving cars)
        if class_ids is not None and len(class_ids) == n_points:
            semantic_cand = ~np.isin(class_ids, list(ELEVATED_CLASS_IDS))
            n_rej_semantic = int(np.sum(~semantic_cand))
        else:
            semantic_cand = np.ones(n_points, dtype=bool)
            n_rej_semantic = 0

        # 2. Surface normal orientation via Open3D
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_xyz)
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamKNN(knn=min(self.knn_normals, max(3, n_points - 1)))
        )
        normals = np.asarray(pcd.normals)

        # Normal orientation: ground normals point predominantly vertical (|n_z| >= min_nz)
        vertical_mask = np.abs(normals[:, 2]) >= self.min_nz
        normal_cand = semantic_cand & vertical_mask
        n_rej_vertical = int(np.sum(semantic_cand & ~vertical_mask))

        # 3. Morphological Progressive Grid: local minimum elevation
        cand_indices = np.where(normal_cand)[0]
        if len(cand_indices) == 0:
            return GroundDetectionResult(
                ground_mask=np.zeros(n_points, dtype=bool),
                ground_points_xyz=np.zeros((0, 3), dtype=np.float64),
                n_ground_points=0,
                n_rejected_semantic=n_rej_semantic,
                n_rejected_vertical=n_rej_vertical,
                n_rejected_elevated=0,
            )

        cand_xyz = points_xyz[cand_indices]
        min_x, min_y = np.min(cand_xyz[:, 0]), np.min(cand_xyz[:, 1])

        cell_x = np.floor((cand_xyz[:, 0] - min_x) / self.grid_cell_size).astype(np.int32)
        cell_y = np.floor((cand_xyz[:, 1] - min_y) / self.grid_cell_size).astype(np.int32)

        # Find min Z per cell
        cell_min_z: dict[tuple[int, int], float] = {}
        for idx in range(len(cand_indices)):
            c_key = (cell_x[idx], cell_y[idx])
            z_val = cand_xyz[idx, 2]
            if c_key not in cell_min_z or z_val < cell_min_z[c_key]:
                cell_min_z[c_key] = z_val

        # Ground test: point Z must be within height_thresh of its cell minimum
        ground_mask = np.zeros(n_points, dtype=bool)
        n_rej_elevated = 0

        for local_idx, global_idx in enumerate(cand_indices):
            c_key = (cell_x[local_idx], cell_y[local_idx])
            min_z = cell_min_z[c_key]
            if cand_xyz[local_idx, 2] <= min_z + self.height_thresh:
                ground_mask[global_idx] = True
            else:
                n_rej_elevated += 1

        ground_pts = points_xyz[ground_mask]

        return GroundDetectionResult(
            ground_mask=ground_mask,
            ground_points_xyz=ground_pts,
            n_ground_points=int(np.sum(ground_mask)),
            n_rejected_semantic=n_rej_semantic,
            n_rejected_vertical=n_rej_vertical,
            n_rejected_elevated=n_rej_elevated,
        )
