"""
Aerial Perception Subsystem.

Coordinates:
1. Aerial semantic segmentation (SegFormer mapped to UAVid taxonomy).
2. Dynamic object detection & tracking (vehicles, pedestrians).
3. Monocular AI relative depth estimation (Depth Anything V2).
4. Scene state classification (High confidence, Uncertain, Low confidence, Unobserved).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence
import cv2
import numpy as np

from frame_processing.segmentation import Segmenter, UAVID_CLASSES, UAVID_CLASS_TO_ID
from depth_fusion.depth_anything import DepthEstimator
from perception.dynamic_objects import DynamicObject, DynamicObjectTracker, MotionStatus
from perception.scene_state import SceneState, SceneStateReport, evaluate_scene_states


@dataclass
class PerceptionResult:
    semantic_mask: np.ndarray                 # (H, W) class IDs
    semantic_confidence: np.ndarray           # (H, W) float [0, 1]
    dynamic_mask: np.ndarray                  # (H, W) bool (True = moving object to exclude from SfM)
    dynamic_objects: list[DynamicObject]      # Discrete detected entities
    depth: np.ndarray | None = None           # (H, W) relative AI depth
    depth_confidence: np.ndarray | None = None # (H, W) float [0, 1]


class AerialPerception:
    """First-class perception engine for UAV aerial imagery."""

    def __init__(self, device: str | None = None, enable_depth: bool = True):
        self.segmenter = Segmenter(device=device)
        self.dynamic_tracker = DynamicObjectTracker()
        self.enable_depth = enable_depth
        self.depth_estimator = DepthEstimator(device=device) if enable_depth else None

    def analyze(
        self,
        frame_bgr: np.ndarray,
        prev_frame_bgr: np.ndarray | None = None,
    ) -> PerceptionResult:
        """Runs the full perception stack on an aerial video/image frame."""
        # 1. Semantic segmentation
        seg_result = self.segmenter.segment(frame_bgr)
        semantic_mask = seg_result.class_id_mask
        semantic_conf = seg_result.confidence_mask

        # 2. Dynamic object tracking & SfM exclusion masking
        dynamic_mask, dynamic_objs = self.dynamic_tracker.detect_and_classify_objects(
            frame_bgr,
            prev_frame_bgr,
            semantic_mask,
            vehicle_class_id=UAVID_CLASS_TO_ID.get("Moving car", 4),
            static_vehicle_class_id=UAVID_CLASS_TO_ID.get("Static car", 5),
            human_class_id=UAVID_CLASS_TO_ID.get("Human", 6),
        )

        # 3. Monocular AI relative depth estimation
        depth = None
        depth_conf = None
        if self.enable_depth and self.depth_estimator is not None:
            depth = self.depth_estimator.predict_relative_depth(frame_bgr)
            # Estimate depth confidence from image gradients (edges and texture provide higher confidence)
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if frame_bgr.ndim == 3 else frame_bgr
            grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
            grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
            edge_mag = np.sqrt(grad_x**2 + grad_y**2)
            edge_conf = np.clip(edge_mag / 100.0, 0.4, 0.95)
            depth_conf = edge_conf.astype(np.float32)

        return PerceptionResult(
            semantic_mask=semantic_mask,
            semantic_confidence=semantic_conf,
            dynamic_mask=dynamic_mask,
            dynamic_objects=dynamic_objs,
            depth=depth,
            depth_confidence=depth_conf,
        )
