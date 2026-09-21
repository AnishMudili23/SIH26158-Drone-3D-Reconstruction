from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

try:
    # torch is only needed to report local GPU availability. This API also runs as a
    # lightweight viewer-only deployment (see requirements-api.txt) that serves
    # already-computed mission outputs and never touches torch/open3d/rasterio at
    # all, so import failure here must degrade gracefully, not crash the app.
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = REPO_ROOT / "outputs"

app = FastAPI(
    title="SIH26158 Single-Pass Drone 3D Reconstruction Platform API",
    version="2.0.0",
    description="Operational REST API powering the Mission Digital Twin frontend and reconstruction orchestration.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    if not _TORCH_AVAILABLE:
        gpu_available, gpu_name = False, "N/A (viewer-only deployment, no local GPU)"
    else:
        gpu_available = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu_available else "CPU"
    return {
        "status": "online",
        "version": "2.0.0",
        "gpu_available": gpu_available,
        "device": gpu_name,
        "repo_root": str(REPO_ROOT),
    }


@app.get("/api/missions")
def list_missions() -> list[dict[str, Any]]:
    missions = []
    if not OUTPUTS_DIR.exists():
        return missions

    for item in sorted(OUTPUTS_DIR.iterdir()):
        if not item.is_dir():
            continue
        deliv_dir = item / "deliverables"
        viewer_dir = item / "viewer_data"
        report_path = deliv_dir / "confidence_report.json"

        mission_info: dict[str, Any] = {
            "id": item.name,
            "name": item.name.replace("_", " ").title(),
            "has_deliverables": deliv_dir.exists(),
            "has_viewer_data": (viewer_dir / "points.json").exists(),
            "status": "COMPLETED" if report_path.exists() else "IN_PROGRESS",
            "modified_time": item.stat().st_mtime,
        }

        if report_path.exists():
            try:
                with open(report_path, "r") as f:
                    rep = json.load(f)
                mission_info["total_frames"] = rep.get("total_input_frames")
                mission_info["registered_frames"] = rep.get("registered_frames")
                mission_info["registration_rate_pct"] = rep.get("registration_rate_pct")
                mission_info["sparse_points"] = rep.get("sparse_points")
                mission_info["telemetry_provenance"] = rep.get("telemetry_provenance")
                mission_info["georeferenced"] = rep.get("georeferenced")
                mission_info["sensor_quality"] = rep.get("sensor_quality")
                mission_info["semantic_quality"] = rep.get("semantic_quality")
                mission_info["volumetric_metrics"] = rep.get("volumetric_metrics")
            except Exception:
                pass

        bldg_path = deliv_dir / "building_instances.json"
        if bldg_path.exists():
            try:
                with open(bldg_path, "r") as f:
                    bdata = json.load(f)
                mission_info["building_count"] = bdata.get("total_buildings", 0)
            except Exception:
                mission_info["building_count"] = 0

        missions.append(mission_info)

    return missions


@app.get("/api/missions/{mission_id}")
def get_mission_detail(mission_id: str) -> dict[str, Any]:
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")

    deliv_dir = mission_dir / "deliverables"
    report_path = deliv_dir / "confidence_report.json"
    if not report_path.exists():
        return {"id": mission_id, "status": "NO_REPORT"}

    with open(report_path, "r") as f:
        report_data = json.load(f)

    # Deliverables file inventory
    files = []
    if deliv_dir.exists():
        for f in deliv_dir.iterdir():
            if f.is_file():
                files.append({
                    "name": f.name,
                    "size_bytes": f.stat().st_size,
                    "url": f"/static/outputs/{mission_id}/deliverables/{f.name}",
                })

    return {
        "id": mission_id,
        "report": report_data,
        "deliverables": files,
    }


@app.get("/api/missions/{mission_id}/buildings")
def get_mission_buildings(mission_id: str) -> dict[str, Any]:
    mission_dir = OUTPUTS_DIR / mission_id
    bldg_path = mission_dir / "deliverables" / "building_instances.json"
    if not bldg_path.exists():
        bldg_path = mission_dir / "viewer_data" / "building_instances.json"
    if not bldg_path.exists():
        return {"total_buildings": 0, "buildings": []}

    with open(bldg_path, "r") as f:
        return json.load(f)


@app.get("/api/missions/{mission_id}/trajectory")
def get_mission_trajectory(mission_id: str) -> dict[str, Any]:
    traj_path = OUTPUTS_DIR / mission_id / "viewer_data" / "trajectory.json"
    if not traj_path.exists():
        raise HTTPException(status_code=404, detail="Trajectory not found.")
    with open(traj_path, "r") as f:
        return json.load(f)


@app.get("/api/missions/{mission_id}/points")
def get_mission_points(mission_id: str) -> dict[str, Any]:
    points_path = OUTPUTS_DIR / mission_id / "viewer_data" / "points.json"
    if not points_path.exists():
        raise HTTPException(status_code=404, detail="Viewer points not found.")
    with open(points_path, "r") as f:
        return json.load(f)


@app.get("/api/missions/{mission_id}/video")
def get_mission_video(mission_id: str) -> dict[str, Any]:
    """Resolves the onboard flight video for a mission, if one exists.

    Missions built from a video input keep the source file directly under their
    output directory; missions built from a folder of still images (e.g. a
    photogrammetry survey) have no onboard video at all. Returns 404 rather than
    a guessed filename so the frontend never renders a broken video element.
    """
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.is_dir():
        raise HTTPException(status_code=404, detail="Mission not found.")
    videos = sorted(mission_dir.glob("*.mp4"))
    if not videos:
        raise HTTPException(status_code=404, detail="No onboard video for this mission.")
    return {"url": f"/static/outputs/{mission_id}/{videos[0].name}"}


# Mount static output files
if OUTPUTS_DIR.exists():
    app.mount("/static/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# Mount viewer bundle
viewer_html_dir = REPO_ROOT / "src" / "viewer"
if viewer_html_dir.exists():
    app.mount("/viewer", StaticFiles(directory=str(viewer_html_dir), html=True), name="viewer")
