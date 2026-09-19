"""Regression tests for the Cityscapes->UAVid class-remapping table and the
moving/static car temporal heuristic in src/frame_processing/segmentation.py — pure
logic, no torch/model loading needed."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from frame_processing.segmentation import (
    CITYSCAPES_ID_TO_NAME,
    CITYSCAPES_TO_UAVID,
    UAVID_CLASS_TO_ID,
    resolve_car_dynamics,
)


def test_every_cityscapes_class_has_a_mapping():
    for cid, name in CITYSCAPES_ID_TO_NAME.items():
        assert name in CITYSCAPES_TO_UAVID, f"Cityscapes class '{name}' has no UAVid mapping"


def test_mapped_uavid_names_are_all_valid_or_car_placeholder():
    for cityscapes_name, uavid_name in CITYSCAPES_TO_UAVID.items():
        assert uavid_name == "__CAR__" or uavid_name in UAVID_CLASS_TO_ID


def test_resolve_car_dynamics_first_frame_defaults_to_moving():
    mask = np.full((20, 20), UAVID_CLASS_TO_ID["Background clutter"], dtype=np.uint8)
    mask[5:10, 5:10] = 255  # unresolved car placeholder
    resolved = resolve_car_dynamics(prev_mask=None, curr_mask=mask)
    assert (resolved[5:10, 5:10] == UAVID_CLASS_TO_ID["Moving car"]).all()


def test_resolve_car_dynamics_stationary_blob_becomes_static():
    prev = np.full((20, 20), UAVID_CLASS_TO_ID["Background clutter"], dtype=np.uint8)
    prev[5:10, 5:10] = 255
    curr = prev.copy()  # identical position -> centroid shift ~0
    resolved = resolve_car_dynamics(prev_mask=prev, curr_mask=curr)
    assert (resolved[5:10, 5:10] == UAVID_CLASS_TO_ID["Static car"]).all()


def test_resolve_car_dynamics_moved_blob_stays_moving():
    prev = np.full((30, 30), UAVID_CLASS_TO_ID["Background clutter"], dtype=np.uint8)
    prev[5:10, 5:10] = 255
    curr = np.full((30, 30), UAVID_CLASS_TO_ID["Background clutter"], dtype=np.uint8)
    curr[20:25, 20:25] = 255  # moved far away
    resolved = resolve_car_dynamics(prev_mask=prev, curr_mask=curr, centroid_shift_threshold_px=8.0)
    assert (resolved[20:25, 20:25] == UAVID_CLASS_TO_ID["Moving car"]).all()
