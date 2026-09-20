"""Regression test for src/reconstruction/colmap_backend.py's images.txt parser —
catches a real desynchronization bug found before running on real ETH3D ground-truth
data: filtering blank lines globally breaks the strict (pose line, POINTS2D line)
pairing the moment any POINTS2D line is legitimately empty."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reconstruction.colmap_backend import _read_images_txt


def test_parses_images_with_empty_points2d_lines(tmp_path):
    # Mimics ETH3D's dslr_calibration_undistorted/images.txt: ground-truth-only
    # calibration exports can have zero POINTS2D correspondences per image.
    content = (
        "# comment header\n"
        "1 1.0 0.0 0.0 0.0 0.0 0.0 0.0 1 image_a.jpg\n"
        "\n"
        "2 0.0 1.0 0.0 0.0 1.0 2.0 3.0 1 image_b.jpg\n"
        "10.5 20.5 5\n"
        "3 0.0 0.0 1.0 0.0 4.0 5.0 6.0 1 image_c.jpg\n"
        "\n"
    )
    path = tmp_path / "images.txt"
    path.write_text(content)

    images = _read_images_txt(path)
    assert len(images) == 3
    assert images[1]["name"] == "image_a.jpg"
    assert images[1]["points2d"] == []
    assert images[2]["name"] == "image_b.jpg"
    assert images[2]["points2d"] == [(10.5, 20.5, 5)]
    assert images[3]["name"] == "image_c.jpg"
    assert images[3]["points2d"] == []
    np.testing.assert_allclose(images[2]["translation"], (1.0, 2.0, 3.0))
