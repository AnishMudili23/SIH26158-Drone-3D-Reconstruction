# AeroMesh 3D — Single-Pass Drone Video to Georeferenced 3D Digital Twin

**SIH 2026 · Problem Statement SIH26158 · NTRO · Robotics & Drones (Software)**

AeroMesh turns a single continuous drone flight video, plus its GPS/IMU/barometer
telemetry, into a **georeferenced, metrically scaled, class-tagged 3D model**. No manual
ground control points are needed. The reconstruction pipeline runs offline on a laptop
GPU, and a web platform (FastAPI + Next.js + CesiumJS) lets you inspect, measure and
audit the results.

> **Honesty first.** Every output carries its own confidence and provenance information.
> Telemetry is tagged `REAL` / `SIMULATED` / `ESTIMATED`, and if GPS is missing the
> pipeline falls back to a `LOCAL_METRIC` frame instead of inventing coordinates. The
> viewer shows "N/A" rather than placeholder numbers when a report is unavailable.

---

## What it produces

| Deliverable | Format |
|---|---|
| Class-tagged point cloud (building / road / tree / vegetation / vehicle / ground) | `.ply`, `.las` / `.laz` (ASPRS 1.4, point format 7) |
| Textured, metrically scaled mesh | `.glb`, `.ply` (vertex-colour and UV-textured variants) |
| Digital Surface / Terrain Model | `dsm.tif`, `dtm.tif` (GeoTIFF) |
| Orthomosaic | `orthomosaic.png` / GeoTIFF |
| Per-building instances and volumetrics | `building_instances.json` |
| Confidence / coverage report (by region and class) | `confidence_report.json` |
| Refined flight trajectory | `refined_trajectory.json` |

## Reconstruction pipeline

```
video + telemetry
   │
   ├─ Phase 1  frame extraction → blur / duplicate filtering → adaptive keyframes
   │           semantic segmentation (UAVid classes) + dynamic-object masking
   ├─ Phase A  FlightSession: GPS/IMU/baro sync, EKF trajectory, provenance tags
   ├─ Phase 2  COLMAP incremental SfM (default geometry path)
   ├─ Phase C  geo-constrained bundle adjustment (GPS priors)
   ├─ Phase 3  Umeyama similarity alignment → metric scale + georeference (ENU/UTM)
   ├─ Phase 5  Depth Anything V2 dense fusion + multi-view consistency + outlier removal
   ├─ Phase 6  confidence tiers, volumetrics, coverage / uncertainty
   └─ Phase 7  class tagging, DSM/DTM, orthomosaic, LAS/LAZ, UV-textured mesh
```

Design rules (from [CLAUDE.md](CLAUDE.md)):

- **COLMAP is the default geometry source.** Any AI geometry model sits behind the
  swappable `estimate_geometry()` interface in `src/common/geometry_interface.py`, so
  nothing depends on a licence-restricted model.
- **6 GB VRAM budget.** Models are chosen to fit an RTX 3050 laptop GPU.
- **Frames are always quality-filtered** before reconstruction.

Full detail: [PRD.md](PRD.md) · [ARCHITECTURE.md](ARCHITECTURE.md) ·
[TECH_STACK.md](TECH_STACK.md) · [ROADMAP.md](ROADMAP.md) · [PROGRESS.md](PROGRESS.md)
(build log, including bugs found and fixed).

## Web platform

| Layer | Stack | Location |
|---|---|---|
| API | FastAPI + Uvicorn | [src/api/](src/api/) |
| Frontend | Next.js 16, React 19, Tailwind 4 | [frontend/](frontend/) |
| 3D viewer | CesiumJS (served at `/viewer/cesium_viewer.html`, embedded by the frontend) | [src/viewer/](src/viewer/) |

Viewer features: georeferenced mesh and point cloud, class-layer toggles, confidence
overlay, click-to-measure, structure inspector, synchronized onboard video, flight
replay from the real reconstructed trajectory, and per-mission report and download.

Main API routes: `GET /api/health`, `GET /api/missions`, `GET /api/missions/{id}` (plus
`/points`, `/trajectory`, `/buildings`, `/video`, `/report`, `/provenance`,
`/download/{asset}`), and `POST` routes for creating missions, uploading
video/telemetry, and `analyze` / `reconstruct` jobs. Interactive docs are at `/docs`.

## Included demo: Zurich Infrastructure Demo

A real drone flight from the public **Zurich Urban MAV** dataset (RPG / ETH Zurich),
with real GPS, IMU, barometer and camera calibration. The finished outputs are
committed under `outputs/zurich_mav_mission/` (about 39 MB) so a fresh deployment shows
a complete mission without needing a GPU.

From its `confidence_report.json`:

| Metric | Value |
|---|---|
| Frames registered | 350 / 350 |
| Sparse points | 32,289 |
| Mean GPS residual | 0.61 m |
| Mean reprojection error | 0.85 px (0.83 px after geo-constrained BA) |
| High-confidence points | 56.2 % |

These numbers describe internal consistency and fit to the flight's GPS. They aren't an
independently surveyed accuracy claim for the whole model. Independent validation so
far was done against ETH3D ground truth and synthetic scenes (see PROGRESS.md).

## Quick start (local)

Requirements: Python 3.11, Node 20+. The full pipeline also needs COLMAP, and a CUDA
GPU for the depth model.

```powershell
# Backend + frontend in two windows (Windows)
.\start.ps1            # or start.bat

# or manually
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt       # full pipeline
$env:PYTHONPATH = ".;src"
.\.venv\Scripts\python -m uvicorn src.api.main:app --port 8000 --reload

npm --prefix frontend install
npm run dev                                           # http://localhost:3000
```

The API is at http://localhost:8000 (docs at `/docs`).

Run the reconstruction on a flight:

```powershell
python -m src.pipeline --help      # single-command end-to-end runner
```

Dataset adapters live in `src/datasets/` (Zurich MAV, UZH-FPV). Benchmarks are in
`scripts/benchmark_datasets.py` and `scripts/run_zurich_mav_benchmark.py`.

### Tests

```powershell
$env:PYTHONPATH = ".;src"
.\.venv\Scripts\python -m pytest tests -q     # 93 tests
npm --prefix frontend run build
```

## Deployment (Render)

[render.yaml](render.yaml) defines two free web services:

| Service | Runtime | Build | Start |
|---|---|---|---|
| `aeromesh-api` | Python 3.11 | `pip install -r requirements-api.txt` | `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT` |
| `aeromesh-web` | Node 20 (`rootDir: frontend`) | `npm install && npm run build` | `npm start` |

This is a **viewer-only** deployment. The API only serves already-computed outputs, so it
uses the light [requirements-api.txt](requirements-api.txt) (no torch / open3d / rasterio),
and `/api/health` reports `gpu_available: false` there. COLMAP and depth fusion stay local.

Setup:

1. On Render, create a **Blueprint** from this repo.
2. After `aeromesh-api` deploys, copy its public URL into `aeromesh-web`'s
   `NEXT_PUBLIC_API_URL` env var. It is baked in at build time, so redeploy the web
   service afterwards.
3. Free instances sleep when idle, so the first request after a pause can take about a
   minute.

## Repository layout

```
src/
  frame_processing/  extraction, quality filter, adaptive keyframes, masking
  telemetry/         FlightSession, EKF trajectory
  geo/               flight metadata, scale alignment, adaptive georeferencing
  reconstruction/    COLMAP backend, geo-constrained BA
  depth_fusion/      Depth Anything V2, multi-view consistency, fusion
  scene/ perception/ semantic voting, ground detection, building instances
  confidence/ accuracy/  confidence report, coverage, uncertainty, benchmarks
  exports/           LAS/LAZ, DSM/DTM, orthomosaic, class tagging, UV texture
  datasets/          Zurich MAV, UZH-FPV adapters
  api/               FastAPI app + mission manager
  viewer/            CesiumJS and Three.js viewers
  pipeline.py        single-command end-to-end runner
frontend/            Next.js mission-studio UI
outputs/             mission outputs (only the Zurich demo is committed)
tests/ scripts/ reports/
```

## Known limitations

- No per-building instance segmentation inspector yet. The inspector's volumetrics are
  reconstruction-wide and labelled as such.
- The confidence overlay is per-point, not a raster grid that shows unobserved cells.
- Fisheye (UZH-FPV) reconstruction isn't wired into the undistortion path.
- Two of the planned benchmark datasets (3DAeroRelief, AirSim ablation) are stubs.
- Stretch phases (VGGT, 3D Gaussian Splatting, cloud-GPU tiering) are not part of the
  core build.

## Data and credits

Zurich Urban MAV (RPG / ETH Zurich), UZH-FPV (RPG / UZH), ETH3D, UAVid class scheme.
Built on COLMAP, Open3D, OpenCV, Depth Anything V2, SegFormer, FastAPI, Next.js, CesiumJS.
