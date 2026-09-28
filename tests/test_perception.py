import numpy as np
import pytest

from perception.dynamic_objects import DynamicObjectTracker, MotionStatus
from perception.scene_state import SceneState, evaluate_scene_states


def test_dynamic_object_tracker_classifies_motion():
    tracker = DynamicObjectTracker(min_motion_px=3.0)

    # Frame 1 and Frame 2: simulated car moving horizontally by 5 pixels
    h, w = 100, 100
    prev_frame = np.full((h, w, 3), 128, dtype=np.uint8)
    curr_frame = np.full((h, w, 3), 128, dtype=np.uint8)

    # Draw moving box
    prev_frame[40:60, 30:50] = 200
    curr_frame[40:60, 35:55] = 200  # shifted by 5px

    semantic_mask = np.zeros((h, w), dtype=int)
    semantic_mask[40:60, 35:55] = 4  # vehicle class

    dyn_mask, objects = tracker.detect_and_classify_objects(
        curr_frame, prev_frame, semantic_mask, vehicle_class_id=4
    )

    assert len(objects) == 1
    obj = objects[0]
    assert obj.class_name == "Vehicle"
    assert obj.motion_status == MotionStatus.MOVING
    assert dyn_mask.any()


def test_scene_states_evaluation():
    confs = np.array([0.95, 0.90, 0.85, 0.70, 0.65, 0.40, 0.30, 0.92, 0.88, 0.55])
    states, report = evaluate_scene_states(confs, unobserved_ratio=0.10)

    assert len(states) == 10
    assert SceneState.OBSERVED_HIGH.value in states
    assert SceneState.OBSERVED_UNCERTAIN.value in states
    assert SceneState.OBSERVED_LOW.value in states
    assert report.unobserved_pct == 10.0
    assert report.observed_high_pct > 0.0
