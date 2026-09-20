import sys
from pathlib import Path
import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datasets.zurich_mav import load_zurich_mav_session
from datasets.uzh_fpv import load_uzh_fpv_session
from telemetry.flight_session import ProvenanceMode

REPO_ROOT = Path(__file__).resolve().parents[1]
ZURICH_DIR = REPO_ROOT / "datasets" / "zurich_mav" / "AGZ_subset"
UZH_FPV_DIR = REPO_ROOT / "datasets" / "uzh_fpv"
UZH_FPV_CALIB = UZH_FPV_DIR / "race_calibration"


@pytest.mark.skipif(not ZURICH_DIR.exists(), reason="Zurich MAV AGZ_subset dataset not present")
def test_zurich_mav_adapter_ingestion():
    session, image_paths, gt_checkpoints = load_zurich_mav_session(ZURICH_DIR)
    
    # Verify session properties
    assert session.provenance == ProvenanceMode.REAL
    assert len(session.frames) == 350
    assert len(image_paths) == 350
    assert session.is_georeferenced is True
    assert len(session.gps_fixes) > 0
    assert len(session.imu_measurements) > 0
    assert len(session.barometer_measurements) > 0
    assert len(gt_checkpoints) == 12

    # Verify camera intrinsics
    cam = session.camera
    assert cam.width == 1920
    assert cam.height == 1080
    assert np.isclose(cam.fx, 893.39, atol=1.0)
    assert np.isclose(cam.fy, 898.33, atol=1.0)
    assert len(cam.distortion_coeffs) == 5

    # Verify first frame interpolation
    f0 = session.frames[0]
    assert f0.gps is not None
    assert np.isclose(f0.gps.latitude, 47.384, atol=1e-3)
    assert np.isclose(f0.gps.longitude, 8.545, atol=1e-3)
    assert f0.position_enu == (0.0, 0.0, 0.0)


@pytest.mark.skipif(not (UZH_FPV_DIR / "img").exists(), reason="UZH-FPV race_3 dataset not present")
def test_uzh_fpv_adapter_ingestion():
    session, image_paths = load_uzh_fpv_session(UZH_FPV_DIR, UZH_FPV_CALIB)

    # Verify session properties
    assert session.provenance == ProvenanceMode.REAL
    assert len(session.frames) == 822
    assert len(image_paths) == 822
    assert session.is_georeferenced is False  # Explicitly no GPS in outdoor race
    assert len(session.gps_fixes) == 0
    assert len(session.imu_measurements) > 5000

    # Verify equidistant fisheye camera model
    cam = session.camera
    assert cam.width == 848
    assert cam.height == 800
    assert cam.model_type == "EQUIDISTANT"
    assert len(cam.distortion_coeffs) == 4

    # Verify telemetry synchronization
    f0 = session.frames[0]
    assert f0.gps is None
    assert f0.position_enu is None
    assert f0.imu is not None
