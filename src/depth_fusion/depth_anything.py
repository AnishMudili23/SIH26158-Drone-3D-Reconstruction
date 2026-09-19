"""
Phase 5 — Monocular depth estimation via Depth Anything V2 (small checkpoint).

Per ARCHITECTURE.md/TECH_STACK.md: Depth Anything V2 is the primary AI depth-fusion
path for MVP (not VGGT — VGGT stays behind the swappable geometry interface as a
Phase 9 stretch goal per CLAUDE.md constraint #1). The "small" checkpoint
(~25M params, ViT-S backbone) is used specifically because it's the version explicitly
called out as fitting the 6GB VRAM budget with headroom (TECH_STACK.md: "avoid the
largest checkpoint").
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"


class DepthEstimator:
    """Lazily loads the model on first use — same pattern as segmentation.Segmenter,
    so importing this module costs nothing until depth estimation is actually run."""

    def __init__(self, device: str | None = None):
        self._model = None
        self._processor = None
        self._device = device

    def _ensure_loaded(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._device = device
        self._processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        self._model = AutoModelForDepthEstimation.from_pretrained(MODEL_ID).to(device).eval()

    def predict_relative_depth(self, image_bgr: np.ndarray) -> np.ndarray:
        """Returns a (H, W) float32 array of *relative* (unscaled) depth — higher value
        = closer to camera (Depth Anything V2's native convention). This is NOT metric
        depth; fusing it with COLMAP's metric-scale sparse points (after Phase 3
        alignment) requires a per-frame local scale/shift fit, done in `fuse_depth.py`.
        """
        import torch

        self._ensure_loaded()
        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        inputs = self._processor(images=rgb, return_tensors="pt").to(self._device)
        with torch.no_grad():
            outputs = self._model(**inputs)
            predicted_depth = outputs.predicted_depth  # (1, h', w')

        depth = torch.nn.functional.interpolate(
            predicted_depth.unsqueeze(1), size=(h, w), mode="bicubic", align_corners=False
        )[0, 0]
        return depth.cpu().numpy().astype(np.float32)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python depth_anything.py <image_path>")
        sys.exit(1)
    img = cv2.imread(sys.argv[1])
    estimator = DepthEstimator()
    depth = estimator.predict_relative_depth(img)
    print(f"Depth map shape: {depth.shape}, range [{depth.min():.3f}, {depth.max():.3f}]")
    out_path = Path(sys.argv[1]).with_suffix(".depth.png")
    normalized = ((depth - depth.min()) / (depth.max() - depth.min() + 1e-9) * 255).astype(np.uint8)
    cv2.imwrite(str(out_path), normalized)
    print(f"Wrote visualization to {out_path}")
