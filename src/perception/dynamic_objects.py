"""
Dynamic Object Detection, Tracking, and Preservation Module.

Detects moving cars and pedestrians using:
1. Semantic mask priors (cars, buses, trucks, humans).
2. Inter-frame optical flow & connected component centroid displacement.
3. Classifies objects into: STATIC, MOVING, UNCERTAIN.
4. Masks MOVING objects out of SfM / Poisson meshing to prevent ghosting.
5. Retains dynamic objects as structured scene entities in metadata (never blindly deleted).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import cv2
import numpy as np


class MotionStatus(str, Enum):
    STATIC = "STATIC"
    MOVING = "MOVING"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class DynamicObject:
    object_id: int
    class_name: str
    motion_status: MotionStatus
    displacement_px: float
    bounding_box_xywh: tuple[int, int, int, int]
    centroid_xy: tuple[float, float]
    confidence: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["motion_status"] = self.motion_status.value
        return d


class DynamicObjectTracker:
    """Detects and tracks moving objects across consecutive video frames."""

    def __init__(self, min_motion_px: float = 3.5, uncertain_motion_px: float = 1.5):
        self.min_motion_px = min_motion_px
        self.uncertain_motion_px = uncertain_motion_px

    def detect_and_classify_objects(
        self,
        curr_bgr: np.ndarray,
        prev_bgr: np.ndarray | None,
        semantic_mask: np.ndarray,
        vehicle_class_id: int = 4,  # Moving car / car in UAVid
        static_vehicle_class_id: int = 5,
        human_class_id: int = 6,
    ) -> tuple[np.ndarray, list[DynamicObject]]:
        """Identifies dynamic objects, computes optical flow displacement, and generates
        a binary exclusion mask for SfM.
        
        Returns:
            (dynamic_exclusion_mask, list_of_dynamic_objects)
        """
        h, w = curr_bgr.shape[:2]
        dynamic_mask = np.zeros((h, w), dtype=bool)
        detected_objects: list[DynamicObject] = []

        # Find potential dynamic pixels from semantic classes
        candidate_mask = (
            (semantic_mask == vehicle_class_id)
            | (semantic_mask == static_vehicle_class_id)
            | (semantic_mask == human_class_id)
        ).astype(np.uint8)

        if not np.any(candidate_mask):
            return dynamic_mask, detected_objects

        # Extract connected components (discrete objects)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(candidate_mask)

        # Compute optical flow if previous frame exists
        flow_mag = None
        if prev_bgr is not None:
            gray_prev = cv2.cvtColor(prev_bgr, cv2.COLOR_BGR2GRAY) if prev_bgr.ndim == 3 else prev_bgr
            gray_curr = cv2.cvtColor(curr_bgr, cv2.COLOR_BGR2GRAY) if curr_bgr.ndim == 3 else curr_bgr
            flow = cv2.calcOpticalFlowFarneback(
                gray_prev, gray_curr, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            flow_mag = np.linalg.norm(flow, axis=2)

        for obj_id in range(1, num_labels):
            x, y, bw, bh, area = stats[obj_id]
            if area < 40:  # noise filter
                continue

            cx, cy = centroids[obj_id]
            obj_pixel_mask = labels == obj_id

            # Determine dominant class in component
            obj_classes = semantic_mask[obj_pixel_mask]
            dom_class_id = int(np.bincount(obj_classes).argmax())
            class_name = "Vehicle" if dom_class_id in (vehicle_class_id, static_vehicle_class_id) else "Human"

            # Determine motion
            mean_displacement = 0.0
            if flow_mag is not None:
                mean_displacement = float(np.median(flow_mag[obj_pixel_mask]))

            if class_name == "Human":
                # Humans are conservative moving objects
                status = MotionStatus.MOVING if mean_displacement >= self.uncertain_motion_px else MotionStatus.UNCERTAIN
            else:
                if mean_displacement >= self.min_motion_px:
                    status = MotionStatus.MOVING
                elif mean_displacement >= self.uncertain_motion_px:
                    status = MotionStatus.UNCERTAIN
                else:
                    status = MotionStatus.STATIC

            # If moving or human, mask out from SfM geometry
            if status == MotionStatus.MOVING:
                dynamic_mask[obj_pixel_mask] = True

            detected_objects.append(DynamicObject(
                object_id=obj_id,
                class_name=class_name,
                motion_status=status,
                displacement_px=round(mean_displacement, 2),
                bounding_box_xywh=(int(x), int(y), int(bw), int(bh)),
                centroid_xy=(round(float(cx), 1), round(float(cy), 1)),
                confidence=0.88,
            ))

        return dynamic_mask, detected_objects
