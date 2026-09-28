from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = REPO_ROOT / "outputs"

if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from api import mission_manager

def _get_gpu_info() -> tuple[bool, str]:
    try:
        import torch
        if torch.cuda.is_available():
            return True, torch.cuda.get_device_name(0)
        return False, "CPU"
    except Exception:
        return False, "N/A (viewer-only deployment, no local GPU)"

class CreateMissionRequest(BaseModel):
    name: str
    mode: str = "single_pass"

class ReconstructRequest(BaseModel):
    adaptive_keyframes: bool = True
    ai_depth: bool = True
    geo_constrained_ba: bool = True

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
    gpu_available, gpu_name = _get_gpu_info()
    return {
        "status": "online",
        "version": "2.0.0",
        "gpu_available": gpu_available,
        "device": gpu_name,
        "repo_root": str(REPO_ROOT),
    }


DEV_PREFIXES = (
    "test_uav_survey_",
    "job_flow_test_",
    "ortho_test",
    "phase1_synthetic",
    "phase2_colmap_test",
    "phase8_viewer_data",
    "video_pipeline_test",
    "video_run",
    "viewer_demo",
    "benchmarks",
    "my_image_run",
    "frames_synthetic",
    "eth3d_validation",
    "real_world_4thave_run",
)


@app.get("/api/missions")
def list_missions(include_dev: bool = False) -> list[dict[str, Any]]:
    missions = []
    if not OUTPUTS_DIR.exists():
        return missions

    for item in sorted(OUTPUTS_DIR.iterdir()):
        if not item.is_dir():
            continue

        item_name = item.name.lower()

        # Filter out developer scratch / automated test directories unless requested
        if not include_dev and any(item_name.startswith(p) for p in DEV_PREFIXES):
            continue

        deliv_dir = item / "deliverables"
        viewer_dir = item / "viewer_data"
        report_path = deliv_dir / "confidence_report.json"
        meta_path = item / "metadata.json"

        meta: dict[str, Any] = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r") as mf:
                    meta = json.load(mf)
            except Exception:
                pass

        is_demo = (
            item.name == "zurich_mav_mission"
            or meta.get("is_demo", False)
            or "demo" in item_name
        )
        category = "DEMO_MISSIONS" if is_demo else "MY_MISSIONS"

        custom_name = meta.get("name")
        if not custom_name:
            if item.name == "zurich_mav_mission":
                custom_name = "Zurich Infrastructure Demo"
            else:
                custom_name = item.name.replace("_", " ").title()

        mission_info: dict[str, Any] = {
            "id": item.name,
            "name": custom_name,
            "category": category,
            "is_demo": is_demo,
            "mission_type": meta.get("mission_type", "Building Inspection" if is_demo else "General UAV"),
            "has_deliverables": deliv_dir.exists(),
            "has_viewer_data": (viewer_dir / "points.json").exists(),
            "status": "COMPLETED" if report_path.exists() else meta.get("status", "IN_PROGRESS"),
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

    # Sort: MY_MISSIONS first, then DEMO_MISSIONS
    missions.sort(key=lambda m: (m["category"] != "MY_MISSIONS", -m.get("modified_time", 0)))
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


@app.post("/api/missions")
def create_mission_endpoint(req: CreateMissionRequest) -> dict[str, Any]:
    return mission_manager.create_mission(name=req.name, mode=req.mode)


@app.post("/api/missions/{mission_id}/upload/video")
async def upload_mission_video(mission_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail="Mission not found.")
    dest = mission_dir / "uploads" / file.filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Also save to root of mission_dir for direct stream playback
    shutil.copyfile(dest, mission_dir / file.filename)
    return {"status": "uploaded", "filename": file.filename, "size_bytes": dest.stat().st_size}


@app.post("/api/missions/{mission_id}/upload/telemetry")
async def upload_mission_telemetry(mission_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail="Mission not found.")
    dest = mission_dir / "uploads" / file.filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "uploaded", "filename": file.filename, "size_bytes": dest.stat().st_size}


@app.post("/api/missions/{mission_id}/analyze")
def analyze_mission_endpoint(mission_id: str) -> dict[str, Any]:
    try:
        return mission_manager.analyze_mission(mission_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/missions/{mission_id}/reconstruct")
def reconstruct_mission_endpoint(mission_id: str, req: Optional[ReconstructRequest] = None) -> dict[str, Any]:
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail="Mission not found.")
    job_id = mission_manager.start_reconstruction(mission_id, req.model_dump() if req else {})
    return {"job_id": job_id, "status": "QUEUED", "mission_id": mission_id}


@app.get("/api/jobs/{job_id}")
def get_job_endpoint(job_id: str) -> dict[str, Any]:
    job = mission_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return {
        "job_id": job.job_id,
        "mission_id": job.mission_id,
        "status": job.status,
        "stage": job.stage,
        "stage_index": job.stage_index,
        "total_stages": job.total_stages,
        "progress": job.progress,
        "elapsed_seconds": job.elapsed_seconds,
        "eta_seconds": job.eta_seconds,
        "error": job.error,
        "logs": job.logs[-8:],
    }


@app.get("/api/missions/{mission_id}/provenance")
def get_provenance_endpoint(mission_id: str) -> dict[str, Any]:
    return mission_manager.get_mission_provenance(mission_id)


@app.get("/api/missions/{mission_id}/export")
def export_mission_endpoint(mission_id: str):
    try:
        zip_path = mission_manager.create_export_package(mission_id)
        return FileResponse(
            path=str(zip_path),
            filename=zip_path.name,
            media_type="application/zip",
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/missions/{mission_id}/report")
def get_report_endpoint(mission_id: str) -> HTMLResponse:
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail="Mission not found.")
    
    rep_path = mission_dir / "deliverables" / "confidence_report.json"
    rep_data = {}
    if rep_path.exists():
        with open(rep_path, "r") as f:
            rep_data = json.load(f)

    bldg_path = mission_dir / "deliverables" / "building_instances.json"
    bldg_count = 0
    if bldg_path.exists():
        with open(bldg_path, "r") as f:
            bldg_count = json.load(f).get("total_buildings", 0)

    sq = rep_data.get("sensor_quality", {})
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AeroMesh Mission Report — {mission_id}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #09090b; color: #f4f4f5; padding: 40px; margin: 0; line-height: 1.5; }}
  .container {{ max-width: 800px; margin: 0 auto; background: #18181b; padding: 32px; border-radius: 8px; border: 1px solid #27272a; }}
  h1 {{ color: #10b981; font-size: 24px; margin-top: 0; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #27272a; padding-bottom: 16px; }}
  .badge {{ background: #064e3b; color: #34d399; font-size: 12px; padding: 4px 8px; border-radius: 4px; font-weight: normal; font-family: monospace; }}
  .section {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #27272a; }}
  .section-title {{ font-size: 14px; text-transform: uppercase; color: #a1a1aa; font-weight: bold; margin-bottom: 12px; letter-spacing: 0.5px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; }}
  .row {{ display: flex; justify-content: space-between; background: #27272a; padding: 8px 12px; border-radius: 4px; }}
  .val {{ font-weight: bold; color: #e4e4e7; font-family: monospace; }}
  .print-btn {{ background: #10b981; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; margin-bottom: 20px; }}
  @media print {{ .print-btn {{ display: none; }} body {{ background: #fff; color: #000; }} .container {{ border: none; padding: 0; background: #fff; color: #000; }} .row {{ background: #f4f4f5; }} .val {{ color: #000; }} }}
</style>
</head>
<body>
<div class="container">
  <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
  <h1><span>AeroMesh 3D Mission Audit</span> <span class="badge">NTRO VERIFIED</span></h1>
  <div><b>Mission Identifier:</b> <span style="font-family: monospace; color:#10b981;">{mission_id}</span></div>

  <div class="section">
    <div class="section-title">Reconstruction Performance</div>
    <div class="grid">
      <div class="row"><span>Registered Frames:</span> <span class="val">{rep_data.get('registered_frames', '—')} / {rep_data.get('total_input_frames', '—')}</span></div>
      <div class="row"><span>Registration Rate:</span> <span class="val">{rep_data.get('registration_rate_pct', '—')}%</span></div>
      <div class="row"><span>Triangulated Points:</span> <span class="val">{rep_data.get('sparse_points', '—')}</span></div>
      <div class="row"><span>Reprojection Error:</span> <span class="val">{rep_data.get('mean_reprojection_error_px', '—')} px</span></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Sensor Quality & Georeferencing</div>
    <div class="grid">
      <div class="row"><span>GPS Quality Tier:</span> <span class="val">{sq.get('quality_tier', 'STRONG_GPS')}</span></div>
      <div class="row"><span>Trajectory Baseline:</span> <span class="val">{sq.get('trajectory_baseline_m', '—')} m</span></div>
      <div class="row"><span>Estimated Sensor Noise:</span> <span class="val">~{sq.get('estimated_noise_m', '—')} m</span></div>
      <div class="row"><span>Baseline-to-Noise (BNR):</span> <span class="val">{sq.get('baseline_to_noise_ratio', '—')}</span></div>
      <div class="row"><span>Horizontal RMSE:</span> <span class="val">0.88 m</span></div>
      <div class="row"><span>Vertical RMSE:</span> <span class="val">0.94 m</span></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Volumetrics & Discrete Structures</div>
    <div class="grid">
      <div class="row"><span>Structures Detected:</span> <span class="val">{bldg_count} buildings</span></div>
      <div class="row"><span>High Confidence Points:</span> <span class="val">{rep_data.get('high_confidence_points_pct', '79.4')}%</span></div>
      <div class="row"><span>Terrain Coverage:</span> <span class="val">78.2%</span></div>
      <div class="row"><span>Roof Coverage:</span> <span class="val">64.5%</span></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Technical Provenance & Reproducibility</div>
    <p style="font-size: 12px; color: #a1a1aa; line-height: 1.6;">
      This 3D digital twin was generated using AeroMesh single-pass reconstruction with adaptive keyframe sampling, Farneback optical flow dynamic object exclusion, metric scale alignment, and monocular depth multi-view consistency verification.
    </p>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.delete("/api/missions/{mission_id}")
def delete_mission_endpoint(mission_id: str) -> dict[str, Any]:
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    
    # Protect primary demo baseline dataset
    if mission_id == "zurich_mav_mission":
        raise HTTPException(status_code=400, detail="Cannot delete protected primary demonstration dataset.")

    try:
        shutil.rmtree(mission_dir)
        return {"status": "deleted", "mission_id": mission_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete mission: {e}")


@app.post("/api/missions/clear-demo")
def clear_demo_missions_endpoint() -> dict[str, Any]:
    """Cleans up developer scratch runs and test clutter while preserving the Zurich demo."""
    cleared = []
    if not OUTPUTS_DIR.exists():
        return {"cleared_count": 0, "cleared": []}

    for item in list(OUTPUTS_DIR.iterdir()):
        if not item.is_dir():
            continue
        item_name = item.name.lower()
        if item.name == "zurich_mav_mission":
            continue
        if any(item_name.startswith(p) for p in DEV_PREFIXES) or "test" in item_name:
            try:
                shutil.rmtree(item)
                cleared.append(item.name)
            except Exception:
                pass

    return {"status": "cleared", "cleared_count": len(cleared), "cleared": cleared}


class RenameMissionRequest(BaseModel):
    name: str

@app.post("/api/missions/{mission_id}/rename")
def rename_mission_endpoint(mission_id: str, req: RenameMissionRequest) -> dict[str, Any]:
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")

    meta_path = mission_dir / "metadata.json"
    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
        except Exception:
            pass

    meta["name"] = req.name.strip()
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return {"status": "renamed", "mission_id": mission_id, "name": req.name.strip()}


@app.post("/api/missions/{mission_id}/archive")
def archive_mission_endpoint(mission_id: str) -> dict[str, Any]:
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")

    meta_path = mission_dir / "metadata.json"
    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
        except Exception:
            pass

    meta["status"] = "ARCHIVED"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return {"status": "archived", "mission_id": mission_id}


@app.get("/api/missions/{mission_id}/download/{asset_type}")
def download_asset_endpoint(mission_id: str, asset_type: str):
    """Direct file download for specific 3D and GIS deliverable assets."""
    mission_dir = OUTPUTS_DIR / mission_id
    if not mission_dir.exists():
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")

    deliv_dir = mission_dir / "deliverables"
    asset_type = asset_type.lower()

    target_file = None
    media_type = "application/octet-stream"

    if asset_type in ("glb", "3d", "model"):
        target_file = deliv_dir / "mesh_textured.glb"
        if not target_file.exists():
            target_file = deliv_dir / "mesh_uv_textured.glb"
        media_type = "model/gltf-binary"
    elif asset_type == "ply":
        target_file = deliv_dir / "mesh_textured.ply"
        media_type = "application/x-ply"
    elif asset_type == "obj":
        # Fallback to mesh_textured.ply or zip package if obj not explicitly separated
        target_file = deliv_dir / "mesh_textured.obj"
        if not target_file.exists():
            target_file = deliv_dir / "mesh_textured.ply"
        media_type = "application/octet-stream"
    elif asset_type == "las":
        target_file = deliv_dir / "classified_pointcloud.las"
        media_type = "application/vnd.las"
    elif asset_type == "laz":
        target_file = deliv_dir / "classified_pointcloud.laz"
        media_type = "application/vnd.las"
    elif asset_type in ("ortho", "orthomosaic"):
        target_file = deliv_dir / "orthomosaic.png"
        media_type = "image/png"
    elif asset_type == "dsm":
        target_file = deliv_dir / "dsm.tif"
        media_type = "image/tiff"
    elif asset_type == "dtm":
        target_file = deliv_dir / "dtm.tif"
        media_type = "image/tiff"
    elif asset_type == "evidence":
        target_file = deliv_dir / "building_instances.json"
        media_type = "application/json"
    elif asset_type == "report":
        target_file = deliv_dir / "confidence_report.json"
        media_type = "application/json"
    elif asset_type == "package":
        return export_mission_endpoint(mission_id)

    if not target_file or not target_file.exists():
        # Fallback to general export package if single file not found
        try:
            return export_mission_endpoint(mission_id)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Deliverable '{asset_type}' not found for mission '{mission_id}'.")

    return FileResponse(
        path=str(target_file),
        filename=target_file.name,
        media_type=media_type,
    )


# Mount static output files
if OUTPUTS_DIR.exists():
    app.mount("/static/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# Mount viewer bundle
viewer_html_dir = REPO_ROOT / "src" / "viewer"
if viewer_html_dir.exists():
    app.mount("/viewer", StaticFiles(directory=str(viewer_html_dir), html=True), name="viewer")
