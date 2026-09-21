from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np

from src.frame_processing.segmentation import UAVID_CLASSES, UAVID_CLASS_TO_ID

NUM_CLASSES = len(UAVID_CLASSES)
BACKGROUND_ID = UAVID_CLASS_TO_ID["Background clutter"]


@dataclass
class SemanticVotingResult:
    class_ids: np.ndarray               # (N,) uint8
    class_names: list[str]              # (N,) human-readable strings
    class_probabilities: np.ndarray     # (N, NUM_CLASSES) float32 posterior distribution
    semantic_confidences: np.ndarray    # (N,) float32 stability margin [0.0, 1.0]
    observation_counts: np.ndarray      # (N,) int32 number of valid camera observations


class MultiViewSemanticVoter:
    """Performs multi-view Bayesian semantic consensus voting across all cameras
    that triangulated each 3D point in COLMAP SfM."""

    def __init__(self, num_classes: int = NUM_CLASSES):
        self.num_classes = num_classes

    def vote_points(
        self,
        point3d_ids: list[int],
        sparse_model: dict,
        masks_dir: str | Path,
    ) -> SemanticVotingResult:
        n_points = len(point3d_ids)
        if n_points == 0:
            return SemanticVotingResult(
                class_ids=np.zeros(0, dtype=np.uint8),
                class_names=[],
                class_probabilities=np.zeros((0, self.num_classes), dtype=np.float32),
                semantic_confidences=np.zeros(0, dtype=np.float32),
                observation_counts=np.zeros(0, dtype=np.int32),
            )

        # Invert COLMAP image points2d into point3D_id -> [(image_id, x, y), ...]
        point_obs: dict[int, list[tuple[int, float, float]]] = {}
        for image_id, img_data in sparse_model.get("images", {}).items():
            for x, y, pid in img_data.get("points2d", []):
                if pid in point3d_ids:
                    point_obs.setdefault(pid, []).append((image_id, x, y))

        # Cache masks
        mask_cache: dict[int, np.ndarray | None] = {}

        def get_mask(image_id: int) -> np.ndarray | None:
            if image_id in mask_cache:
                return mask_cache[image_id]
            img_meta = sparse_model.get("images", {}).get(image_id)
            if not img_meta:
                mask_cache[image_id] = None
                return None
            name = img_meta["name"]
            mask_path = Path(masks_dir) / (Path(name).stem + "_mask.png")
            mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED) if mask_path.exists() else None
            mask_cache[image_id] = mask
            return mask

        class_ids = np.full(n_points, BACKGROUND_ID, dtype=np.uint8)
        class_probs = np.zeros((n_points, self.num_classes), dtype=np.float32)
        sem_conf = np.zeros(n_points, dtype=np.float32)
        obs_counts = np.zeros(n_points, dtype=np.int32)

        for i, pid in enumerate(point3d_ids):
            observations = point_obs.get(pid, [])
            if not observations:
                # Default background with zero confidence
                class_probs[i, BACKGROUND_ID] = 1.0
                continue

            votes = np.zeros(self.num_classes, dtype=np.float32)
            valid_obs = 0

            for image_id, x, y in observations:
                mask = get_mask(image_id)
                if mask is None:
                    continue
                h, w = mask.shape[:2]
                xi, yi = int(round(x)), int(round(y))
                if 0 <= yi < h and 0 <= xi < w:
                    cid = int(mask[yi, xi])
                    if 0 <= cid < self.num_classes:
                        # Center-weighting: observations closer to center get slightly higher weight
                        # (reduces edge distortion and boundary inaccuracies)
                        cx, cy = w / 2.0, h / 2.0
                        norm_dist = np.sqrt(((xi - cx) / cx) ** 2 + ((yi - cy) / cy) ** 2) / np.sqrt(2.0)
                        weight = float(np.clip(1.0 - 0.3 * norm_dist, 0.5, 1.0))

                        votes[cid] += weight
                        valid_obs += 1

            obs_counts[i] = valid_obs

            if valid_obs == 0:
                class_probs[i, BACKGROUND_ID] = 1.0
                class_ids[i] = BACKGROUND_ID
                sem_conf[i] = 0.0
                continue

            total_weight = np.sum(votes)
            probs = votes / max(total_weight, 1e-6)
            class_probs[i] = probs

            # Top class
            top_class = int(np.argmax(probs))
            class_ids[i] = top_class

            # Margin between top-1 and top-2
            sorted_probs = np.sort(probs)[::-1]
            if len(sorted_probs) > 1:
                margin = sorted_probs[0] - sorted_probs[1]
                # High confidence when top class dominates (e.g. 0.95 vs 0.05 -> 0.90 margin)
                sem_conf[i] = float(np.clip(margin + 0.1 * min(valid_obs, 5), 0.0, 1.0))
            else:
                sem_conf[i] = float(sorted_probs[0])

        id_to_name = {v: k for k, v in UAVID_CLASS_TO_ID.items()}
        class_names = [id_to_name.get(int(cid), "Background clutter") for cid in class_ids]

        return SemanticVotingResult(
            class_ids=class_ids,
            class_names=class_names,
            class_probabilities=class_probs,
            semantic_confidences=sem_conf,
            observation_counts=obs_counts,
        )
