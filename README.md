# 🛰️ AeroMesh 3D — Single-Pass Drone Video → Georeferenced 3D Digital Twin · SIH 2026 · PS 26158 (NTRO)

Feed in **one continuous drone flight video plus its GPS / IMU / barometer telemetry**
and get back a **georeferenced, metrically scaled, class-tagged 3D model** (mesh, point
cloud, DSM/DTM, orthomosaic) with a **confidence report that says how much of it you can
trust**. No ground control points. The reconstruction runs locally on a laptop GPU, and a
web platform lets you inspect, measure and audit the result in the browser.

![Pipeline](https://img.shields.io/badge/Reconstruction-Local%20%7C%20COLMAP-2ea44f)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Depth](https://img.shields.io/badge/Depth-Depth%20Anything%20V2-orange)
![API](https://img.shields.io/badge/API-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-Next.js%2016-black)
![Viewer](https://img.shields.io/badge/Viewer-CesiumJS-5636d3)
![Deploy](https://img.shields.io/badge/Deploy-Render-46e3b7)
![Tests](https://img.shields.io/badge/Tests-93%20passing-brightgreen)
![SIH 2026](https://img.shields.io/badge/SIH%202026-PS%2026158-ff6f00)

- **Problem statement:** generate an accurate, textured, georeferenced 3D model of a scene
  (terrain, buildings, roads, vegetation) from a single drone-pass video. Full text in
  [PRD.md](PRD.md).
- **Design and the reasoning behind each non-obvious choice:** [ARCHITECTURE.md](ARCHITECTURE.md),
  [TECH_STACK.md](TECH_STACK.md), and the full build log in [PROGRESS.md](PROGRESS.md).

## 🌐 Live demo

| Service | URL |
|---|---|
| Web app (Next.js + CesiumJS) | https://aeromesh-web.onrender.com |
| API health | https://aeromesh-api.onrender.com/api/health |
| API docs | https://aeromesh-api.onrender.com/docs |

Hosted on Render's free tier, so the first request after idle can take about a minute.
The hosted build is **viewer-only**: it serves the pre-computed Zurich demo mission. The
reconstruction pipeline itself runs locally (see below).

---

## ✨ What it does

| Capability | How |
|---|---|
| Quality-gated frame selection | Extraction → Laplacian blur filter → perceptual-hash dedupe → adaptive keyframes (60–80 % overlap target) |
| Semantic + dynamic masking | UAVid-class segmentation (building / road / tree / vegetation / vehicle / ground); moving cars and people masked out |
| Sensor fusion | `FlightSession` syncs GPS / IMU / barometer; a 6-DoF EKF produces the trajectory with covariance |
| Real geometry | COLMAP incremental SfM, then geo-constrained bundle adjustment using GPS priors |
| Metric scale + georeference | Umeyama similarity alignment to ENU / UTM, no GCPs |
| Dense reconstruction | Depth Anything V2 fused with multi-view consistency checks and outlier removal |
| GIS deliverables | Class-tagged `.las` / `.laz` (ASPRS 1.4), `.ply`, `.glb` mesh (vertex-colour and UV-textured), DSM / DTM / orthomosaic |
| Honest reporting | Confidence tiers, coverage, GPS residual, reprojection error and volumetrics, by region and semantic class |
| Browser viewer | CesiumJS: layer toggles, confidence overlay, click-to-measure, structure inspector, synced onboard video, flight replay |
| Never fakes data | Telemetry tagged `REAL` / `SIMULATED` / `ESTIMATED`; no GPS means a `LOCAL_METRIC` frame, not invented coordinates |

---

## 🧠 How it works

```
INPUT        drone video + GPS / IMU / baro telemetry (+ optional calibration)

FRAMES       extract ─▶ blur / duplicate filter ─▶ adaptive keyframes
             segment (UAVid classes) ─▶ mask dynamic objects

TELEMETRY    FlightSession (provenance-tagged) ─▶ EKF trajectory + covariance

GEOMETRY     COLMAP SfM ─▶ geo-constrained BA ─▶ Umeyama scale + georeference
             (default path; AI geometry sits behind estimate_geometry(), optional)

DENSE        Depth Anything V2 ─▶ affine align ─▶ multi-view consistency ─▶ outlier removal

OUTPUTS      class tagging ─▶ LAS/LAZ · PLY · GLB · DSM/DTM · orthomosaic
             confidence tiers + coverage + volumetrics ─▶ confidence_report.json

PLATFORM     FastAPI (/api/*) ◀── HTTP ──▶ Next.js UI ──▶ embedded CesiumJS viewer
```

Key decisions (details in [ARCHITECTURE.md](ARCHITECTURE.md)):

- **COLMAP is the default geometry source.** Any AI geometry model (e.g. VGGT) sits behind
  the swappable `estimate_geometry()` interface in
  [src/common/geometry_interface.py](src/common/geometry_interface.py). Nothing depends on a
  licence-restricted model.
- **Built for 6 GB VRAM.** Every model is chosen to fit an RTX 3050 laptop GPU, with a
  CPU or cloud fallback where it doesn't.
- **Never process every raw frame.** Quality filtering always runs first.
- **Confidence is a first-class output**, not an afterthought. Every deliverable ships
  with its provenance and trust information.
- **Real data is the source of truth.** Synthetic scenes are a regression harness only;
  validation uses real flights (Zurich MAV) and ETH3D ground truth.

---

## 📦 Included demo: Zurich Infrastructure Demo

A real flight from the public **Zurich Urban MAV** dataset (RPG / ETH Zurich) with real
GPS, IMU, barometer and camera calibration. Finished outputs are committed under
`outputs/zurich_mav_mission/` (about 39 MB), so a fresh deploy shows a complete mission
with no GPU.

From its [confidence_report.json](outputs/zurich_mav_mission/deliverables/confidence_report.json):

| Metric | Value |
|---|---|
| Frames registered | 350 / 350 |
| Sparse points | 32,289 |
| Mean GPS residual | 0.61 m |
| Mean reprojection error | 0.85 px (0.83 px after geo-constrained BA) |
| High-confidence points | 56.2 % |

These describe internal consistency and fit to the flight's own GPS. They aren't an
independently surveyed accuracy claim for the whole model.

---

## 📁 Repo layout

```
src/
├── frame_processing/   extraction, quality filter, adaptive keyframes, masking
├── telemetry/          FlightSession, EKF trajectory
├── geo/                flight metadata, scale alignment, adaptive georeferencing
├── reconstruction/     COLMAP backend, geo-constrained bundle adjustment
├── depth_fusion/       Depth Anything V2, multi-view consistency, fusion
├── scene/ perception/  semantic voting, ground detection, building instances
├── confidence/         confidence report
├── accuracy/           coverage, uncertainty, scale / trajectory / geo accuracy
├── exports/            LAS/LAZ, DSM/DTM, orthomosaic, class tagging, UV texture
├── datasets/           Zurich MAV and UZH-FPV adapters
├── common/             coordinate frames, alignment, estimate_geometry() interface
├── api/                FastAPI app + mission manager
├── viewer/             CesiumJS and Three.js viewers
└── pipeline.py         single-command end-to-end runner

frontend/               Next.js mission-studio UI
outputs/                mission outputs (only the Zurich demo is committed)
scripts/                benchmarks, dataset runners, viewer tests
tests/                  93 pytest tests
reports/                Phase 0 feasibility + benchmark reports
render.yaml             Render Blueprint (API + web)
```

---

## 🚀 Quick start

Requirements: Python 3.11, Node 20+. The full pipeline also needs **COLMAP** and, for the
depth model, an NVIDIA GPU. The viewer and API alone need neither.

```powershell
# 1. environment
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt        # full pipeline
npm --prefix frontend install

# 2. run the platform (backend :8000 + frontend :3000)
.\start.ps1                                            # or start.bat

# 3. or run the pieces by hand
$env:PYTHONPATH = ".;src"
.\.venv\Scripts\python -m uvicorn src.api.main:app --port 8000 --reload
npm run dev
```

Open http://localhost:3000. The API docs are at http://localhost:8000/docs.

### Run the reconstruction

```powershell
python -m src.pipeline --help
python -m src.pipeline --input <video> --gps-log <gps.csv> --adaptive-keyframes --geo-constrained-ba
```

---

## ⚡ Everything you can run

| Command | What it does |
|---|---|
| `.\start.ps1` | launch API + frontend in two windows |
| `python -m src.pipeline ...` | end-to-end reconstruction from video + telemetry |
| `python -m src.feasibility.run_phase0` | Phase 0 feasibility harness (GPU, scale recovery, coverage) |
| `python scripts/run_zurich_mav_benchmark.py` | reconstruct and score the Zurich MAV flight |
| `python scripts/benchmark_datasets.py` | multi-dataset benchmark runner |
| `python scripts/validate_against_eth3d.py` | validate against ETH3D laser ground truth |
| `python -m pytest tests -q` | 93 regression tests |
| `npm --prefix frontend run build` | production frontend build |

### API

`GET /api/health` · `GET /api/missions` · `GET /api/missions/{id}` (plus `/points`,
`/trajectory`, `/buildings`, `/video`, `/report`, `/provenance`, `/download/{asset}`) ·
`POST /api/missions` · `POST .../upload/video` · `POST .../upload/telemetry` ·
`POST .../analyze` · `POST .../reconstruct` · `GET /api/jobs/{id}`.

---

## ☁️ Deployment (Render)

[render.yaml](render.yaml) defines two free web services:

| Service | Runtime | Build | Start |
|---|---|---|---|
| `aeromesh-api` | Python 3.11 | `pip install -r requirements-api.txt` | `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT` |
| `aeromesh-web` | Node 20 (`rootDir: frontend`) | `npm install && npm run build` | `npm start` |

The API only serves already-computed outputs, so it uses the light
[requirements-api.txt](requirements-api.txt) (no torch / open3d / rasterio, which also
avoids rasterio's system GDAL). `/api/health` reports `gpu_available: false` there.

Set `NEXT_PUBLIC_API_URL` on `aeromesh-web` to the API's public URL. It is baked in at
build time, so redeploy the web service after changing it.

---

## 🚧 Hard constraints — do not violate these

- **Never make VGGT (or any licence-restricted model) the only geometry source.** COLMAP
  stays the default path.
- **Stay within 6 GB VRAM** unless there's an explicit CPU or cloud-GPU fallback.
- **Always quality-filter frames** before reconstruction. No "quick demo" exceptions.
- **Don't present raw model output as ground truth.** Ship confidence and provenance with
  every output.

---

## 🧭 Known limitations

- The structure inspector's volumetrics are reconstruction-wide and labelled as such;
  there is no per-building instance inspection yet.
- The confidence overlay is per-point, not a raster grid that shows unobserved cells.
- Fisheye (UZH-FPV) reconstruction isn't wired into the undistortion path.
- Two planned benchmark datasets (3DAeroRelief, AirSim ablation) are stubs.
- Stretch phases (VGGT, 3D Gaussian Splatting, cloud-GPU tiering) are outside the core build.

---

## 📖 Documentation

| File | What's in it |
|---|---|
| [PRD.md](PRD.md) | problem statement, goals, success targets, judging-rubric alignment |
| [ARCHITECTURE.md](ARCHITECTURE.md) | pipeline design and the reasoning behind each choice |
| [TECH_STACK.md](TECH_STACK.md) | library and model choices, the VRAM budget |
| [ROADMAP.md](ROADMAP.md) | phased plan with definitions of done |
| [PROGRESS.md](PROGRESS.md) | full build log, including bugs found and fixed |
| [reports/phase0_report.md](reports/phase0_report.md) | feasibility results |

---

## 📝 Data attribution

**Zurich Urban MAV** dataset (RPG, ETH Zurich) and **UZH-FPV** (RPG, UZH) for real-flight
validation; **ETH3D** for ground-truth reconstruction scoring; **UAVid** class scheme for
semantic labels. Built on COLMAP, Open3D, OpenCV, Depth Anything V2, SegFormer, FastAPI,
Next.js and CesiumJS.

---

<p align="center">Built for <b>Smart India Hackathon 2026</b> · Problem Statement 26158 (NTRO)</p>
