"""
Phase 1 — Semantic segmentation pass, mapped to UAVid's 8 classes.

Per TECH_STACK.md: "SegFormer (or similar) fine-tuned/mapped to UAVid's 8 classes" —
mapping is the explicitly sanctioned lighter-weight path vs. fine-tuning from scratch,
which would need the UAVid training set (gated behind manual registration at uavid.nl;
see PROGRESS.md Phase 1 entry) plus real training compute.

We use a Cityscapes-pretrained SegFormer-B0 (nvidia/segformer-b0-finetuned-cityscapes-
1024-1024): tiny (~3.8M param encoder), fits the 6GB VRAM budget with headroom, and
Cityscapes' 19 classes cover urban driving scenes closely enough to remap onto UAVid's 8
(both are urban/aerial-adjacent scene taxonomies — building, road, vegetation, vehicle,
person all have direct Cityscapes analogues).

Known mapping limitation (log honestly, don't hide it): Cityscapes' single "vegetation"
class doesn't distinguish trees from low vegetation the way UAVid does. We map
"vegetation" -> Tree and "terrain" -> Low vegetation as the closest available split, but
this is an approximation, not a trained distinction. Revisit if/when real UAVid-labeled
data is available to fine-tune directly.

"Moving car" vs "Static car" isn't a Cityscapes distinction either (it has one "car"
class) — ARCHITECTURE.md notes this needs no separate model, so we derive it from simple
frame-to-frame centroid displacement of car-class connected components (a car blob whose
centroid moves more than a small pixel threshold between consecutive keyframes is
"moving"; ARCHITECTURE.md's whole point in masking dynamic objects is to protect SfM, so
a conservative/aggressive-toward-"moving" threshold is the safer failure mode).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

MODEL_ID = "nvidia/segformer-b0-finetuned-cityscapes-1024-1024"

UAVID_CLASSES = [
    "Building",
    "Road",
    "Tree",
    "Low vegetation",
    "Moving car",
    "Static car",
    "Human",
    "Background clutter",
]
UAVID_CLASS_TO_ID = {name: i for i, name in enumerate(UAVID_CLASSES)}
DYNAMIC_CLASSES = {"Moving car", "Human"}  # masked out before reconstruction (ARCHITECTURE.md)

# Cityscapes trainId -> label name (standard 19-class Cityscapes taxonomy).
CITYSCAPES_ID_TO_NAME = {
    0: "road", 1: "sidewalk", 2: "building", 3: "wall", 4: "fence", 5: "pole",
    6: "traffic light", 7: "traffic sign", 8: "vegetation", 9: "terrain", 10: "sky",
    11: "person", 12: "rider", 13: "car", 14: "truck", 15: "bus", 16: "train",
    17: "motorcycle", 18: "bicycle",
}

# Explicit, documented mapping: Cityscapes name -> UAVid class.
# Car-family classes map to a placeholder resolved by the temporal moving/static split.
CITYSCAPES_TO_UAVID = {
    "building": "Building",
    "road": "Road",
    "sidewalk": "Road",
    "vegetation": "Tree",
    "terrain": "Low vegetation",
    "person": "Human",
    "rider": "Human",
    "car": "__CAR__",
    "truck": "__CAR__",
    "bus": "__CAR__",
    "motorcycle": "__CAR__",
    "bicycle": "__CAR__",
    "wall": "Background clutter",
    "fence": "Background clutter",
    "pole": "Background clutter",
    "traffic light": "Background clutter",
    "traffic sign": "Background clutter",
    "sky": "Background clutter",
    "train": "Background clutter",
}


class Segmenter:
    """Lazily loads the model on first use (heavy import — never pay this cost for
    code paths, like Phase 0, that don't need it)."""

    def __init__(self, device: str | None = None):
        self._model = None
        self._processor = None
        self._device = device

    def _ensure_loaded(self):
        if self._model is not None:
            return
        import torch
        from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._device = device
        self._processor = SegformerImageProcessor.from_pretrained(MODEL_ID)
        self._model = SegformerForSemanticSegmentation.from_pretrained(MODEL_ID).to(device).eval()

    def predict_cityscapes_mask(self, image_bgr: np.ndarray) -> np.ndarray:
        """Returns a (H, W) uint8 array of Cityscapes trainIds, at original resolution."""
        import torch

        self._ensure_loaded()
        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        inputs = self._processor(images=rgb, return_tensors="pt").to(self._device)
        with torch.no_grad():
            logits = self._model(**inputs).logits  # (1, num_classes, h', w')
        upsampled = torch.nn.functional.interpolate(
            logits, size=(h, w), mode="bilinear", align_corners=False
        )
        pred = upsampled.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)
        return pred

    def predict_uavid_mask(self, image_bgr: np.ndarray) -> np.ndarray:
        """Returns a (H, W) uint8 array of UAVID_CLASS_TO_ID values (cars left as a
        placeholder id 255, resolved to Moving/Static by `resolve_car_dynamics`)."""
        cityscapes_mask = self.predict_cityscapes_mask(image_bgr)
        uavid_mask = np.full_like(cityscapes_mask, UAVID_CLASS_TO_ID["Background clutter"])

        for cid, cname in CITYSCAPES_ID_TO_NAME.items():
            uavid_name = CITYSCAPES_TO_UAVID.get(cname, "Background clutter")
            if uavid_name == "__CAR__":
                uavid_mask[cityscapes_mask == cid] = 255  # unresolved car placeholder
            else:
                uavid_mask[cityscapes_mask == cid] = UAVID_CLASS_TO_ID[uavid_name]
        return uavid_mask


def resolve_car_dynamics(
    prev_mask: np.ndarray | None,
    curr_mask: np.ndarray,
    centroid_shift_threshold_px: float = 8.0,
) -> np.ndarray:
    """Resolve id-255 car placeholders into Moving car / Static car via connected-
    component centroid tracking against the previous keyframe's car blobs.

    First frame (no prev_mask) or an unmatched blob defaults to "Moving car" — the
    conservative choice, since ARCHITECTURE.md masks dynamic classes out before SfM and
    an incorrectly-kept parked car is worse for reconstruction than an incorrectly-masked
    one.
    """
    resolved = curr_mask.copy()
    car_binary = (curr_mask == 255).astype(np.uint8)
    if not car_binary.any():
        return resolved

    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(car_binary, connectivity=8)

    prev_centroids = []
    if prev_mask is not None:
        prev_car_binary = (prev_mask == 255).astype(np.uint8)
        if prev_car_binary.any():
            _, _, _, prev_centroids_arr = cv2.connectedComponentsWithStats(prev_car_binary, connectivity=8)
            prev_centroids = prev_centroids_arr[1:]  # drop background label 0

    moving_id = UAVID_CLASS_TO_ID["Moving car"]
    static_id = UAVID_CLASS_TO_ID["Static car"]

    for label_id in range(1, n_labels):  # skip background label 0
        blob_mask = labels == label_id
        centroid = centroids[label_id]

        is_moving = True  # conservative default
        if len(prev_centroids) > 0:
            dists = np.linalg.norm(prev_centroids - centroid, axis=1)
            if dists.min() <= centroid_shift_threshold_px:
                is_moving = False

        resolved[blob_mask] = moving_id if is_moving else static_id

    return resolved


@dataclass
class SegmentationRecord:
    frame_path: str
    mask_path: str
    class_pixel_fractions: dict


def segment_keyframes(
    frame_paths: list[str],
    output_dir: str | Path,
    segmenter: Segmenter | None = None,
) -> list[SegmentationRecord]:
    """Segments frames in temporal order (needed for the moving/static car heuristic)
    and writes one .png class-id mask per frame."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    segmenter = segmenter or Segmenter()

    records = []
    prev_mask = None
    for path in frame_paths:
        img = cv2.imread(path)
        if img is None:
            continue
        uavid_mask = segmenter.predict_uavid_mask(img)
        resolved_mask = resolve_car_dynamics(prev_mask, uavid_mask)
        prev_mask = resolved_mask

        mask_path = output_dir / (Path(path).stem + "_mask.png")
        cv2.imwrite(str(mask_path), resolved_mask)

        total = resolved_mask.size
        fractions = {
            name: float((resolved_mask == cid).sum()) / total
            for name, cid in UAVID_CLASS_TO_ID.items()
        }
        records.append(SegmentationRecord(frame_path=path, mask_path=str(mask_path),
                                           class_pixel_fractions=fractions))
    return records


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python segmentation.py <frames_dir> <output_masks_dir>")
        sys.exit(1)
    frames_dir = Path(sys.argv[1])
    paths = sorted(str(p) for p in frames_dir.glob("*.jpg"))
    records = segment_keyframes(paths, sys.argv[2])
    print(json.dumps([asdict(r) for r in records], indent=2)[:2000])
