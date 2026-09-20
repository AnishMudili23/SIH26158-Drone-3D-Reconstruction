# ARCHITECTURE — SIH26158 Single-Pass Drone 3D Reconstruction

## Core Design Principle

**Sensor-Fused, Uncertainty-Aware 4D Reconstruction.** Don't build a brittle `Video → AI → 3D Model` pipeline. Build:

> **Video + GPS + IMU + Barometer + Camera Model → Sensor-Fused 4D Reconstruction → Metric 3D Model → Uncertainty-Aware GIS Digital Twin**

Classical geometry (COLMAP, multi-view geometry, Extended Kalman Filtering) provides the defensible, metric backbone. AI models (aerial segmentation, Depth Anything V2 monocular depth) provide semantic metadata and uncertainty-weighted geometric priors. Every reconstructed deliverable carries verifiable confidence bounds.

---

## High-Level System Architecture

```text
                         SINGLE DRONE PASS
                              │
                ┌─────────────┴─────────────┐
                │                           │
             VIDEO                    FLIGHT TELEMETRY
                │                           │
                │                    ┌──────┼─────────┐
                │                    │      │         │
                │                   GPS    IMU     BAROMETER
                │                    │      │         │
                └──────────┬─────────┴──────┴─────────┘
                           │
                           ▼
                 SENSOR TIME SYNCHRONIZATION
              (sub-millisecond alignment, FlightSession)
                           │
                           ▼
                 CAMERA CALIBRATION & INTRINSICS
             (fx, fy, cx, cy, radial/tangential distortion)
                           │
                           ▼
                 INTELLIGENT KEYFRAME ENGINE
          ┌────────────────┼────────────────┐
          │                │                │
     Blur Score       Exposure/SSIM     Parallax / Overlap (60-80%)
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                  DYNAMIC OBJECT MASKING
              ┌────────────┴────────────┐
              │                         │
         Static Scene              Dynamic Objects
              │                    (moving cars, humans)
              ▼                         │
      FEATURE EXTRACTION                X (masked out)
              │
              ▼
       TEMPORAL MATCHING
              │
              ▼
       VISUAL ODOMETRY / SfM
              │
              ▼
       GPS + IMU + BARO TRAJECTORY FUSION (EKF)
              │
              ▼
        GEO-CONSTRAINED BUNDLE ADJUSTMENT
              │
              ▼
        METRIC CAMERA POSES & TRAJECTORY
              │
       ┌──────┴─────────┐
       │                │
       ▼                ▼
   Sparse SfM       Dense MVS
       │                │
       │          + Depth Prior (Depth Anything V2)
       │                │
       └───────┬────────┘
               ▼
         MULTI-VIEW DEPTH CONSISTENCY FILTERING
         (cross-camera reprojection consensus)
               │
               ▼
        DENSE POINT CLOUD (Confidence-Weighted)
               │
               ▼
       STATISTICAL & RADIUS OUTLIER REMOVAL
               │
               ▼
      SEMANTIC POINT TAGGING (Aerial Taxonomy)
               │
               ▼
      CLASS-SPECIFIC SURFACE RECONSTRUCTION
       ┌───────┼────────────────────────┐
       ▼       ▼                        ▼
    Terrain  Buildings             Vegetation
    (DTM)    (Surface Mesh)        (Point Cloud / Splat)
       │       │                        │
       └───────┼────────────────────────┘
               ▼
        UV TEXTURE MAPPING & ATLAS
        (triangle visibility + optimal view selection)
               │
        ┌──────┼────────┬───────────┐
        ▼      ▼        ▼           ▼
      Mesh   Point     DSM/DTM   Orthomosaic
      (.glb) Cloud    (GeoTIFF)   (GeoTIFF)
             (.las/.laz)
        │      │        │           │
        └──────┴────────┴───────────┘
                       │
                       ▼
            METRIC ACCURACY & UNCERTAINTY ENGINE
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    Geometry       Coverage       Semantic
    Confidence     Confidence     Confidence
   (Reproj, Ray)  (Categorical)  (Class Stability)
        │              │              │
        └──────────────┼──────────────┘
                       ▼
          OPERATIONAL CESIUM DIGITAL TWIN
      - Mission Flight Replay & Frustum Tracking
      - Categorical Layer Toggles (Buildings, Roads, Veg, Terrain)
      - 4-Tier Uncertainty Heatmap (Green, Yellow, Red, Gray)
      - Interactive Structure Inspector (Height, Footprint, Volume)
      - Metric 3D Measurement & Elevation Profiles
```

---

## Subsystem Breakdown & Component Responsibilities

| Subsystem | Component | Responsibility | Tech / Library |
|---|---|---|---|
| **Input & Telemetry** | `FlightSession` | Synchronizes video frames with high-rate GPS, IMU, and Barometer. Strictly enforces provenance (`REAL`, `SIMULATED`, `ESTIMATED`). | Python `dataclasses`, `scipy.interpolate` |
| **Input & Telemetry** | `EKF Trajectory` | Continuous 6-DoF state propagation (accel, gyro) with GPS and barometric height updates. | Extended Kalman Filter, `numpy` |
| **Frame Processing** | `AdaptiveKeyframeEngine` | Selects minimal frame subset preserving 60–80% mutual overlap, high contrast, and sharp features. | OpenCV, `numpy` |
| **Frame Processing** | `DynamicMasking` | Identifies and tracks dynamic moving objects to exclude them from SfM bundle adjustment. | SegFormer, optical flow |
| **Reconstruction** | `ColmapBackend` | Incremental Structure-from-Motion, camera pose estimation, and sparse triangulation. | COLMAP CLI, CUDA |
| **Reconstruction** | `GeoConstrainedBA` | Incorporates EKF trajectory positions and camera orientation priors into geometry optimization. | Ceres / COLMAP priors |
| **Dense Depth** | `DepthPrior` | Monocular relative depth maps for every selected keyframe. | Depth Anything V2 (Torch, FP16) |
| **Dense Depth** | `MultiviewConsistency` | Forward-backward reprojection checks across adjacent camera views to accept/reject AI depth. | Custom multi-view reprojection |
| **Dense Depth** | `DepthFusion` | Confidence-weighted blending of MVS depth and verified AI depth priors. | Custom, Open3D |
| **Point Cloud** | `OutlierRemoval` | Statistical and radius-based noise filtering to remove floating artifacts. | Open3D |
| **Classification** | `ClassTagging` | Projects multi-view aerial segmentation labels onto 3D points; computes label agreement. | Custom multi-view voting |
| **Surface & Texture** | `SurfaceReconstruction` | Partitioned reconstruction: DTM for terrain, Poisson/Alpha shapes for buildings, point/splat for trees. | Open3D, `scipy.spatial` |
| **Surface & Texture** | `TextureMapper` | Raycasts triangle visibility, scores camera view angles, projects UVs, and packs texture atlas. | Trimesh / Open3D, Pillow |
| **GIS Exports** | `LasExporter` | ASPRS 1.4 Point Format 7 (`.las` / `.laz`) with 8-bit classification, RGB, intensity, and CRS GeoKeys. | `laspy[lazrs]` |
| **GIS Exports** | `RasterExporter` | High-resolution DSM and DTM GeoTIFFs, orthomosaic raster with spatial bounds. | Rasterio, GDAL, OpenCV |
| **Accuracy Subsystem** | `MetricAccuracy` | Computes ATE RMSE, RPE, scale error %, horizontal/vertical RMSE, and Chamfer distance. | `src/accuracy/` |
| **Uncertainty Subsystem**| `UncertaintyEngine` | Calculates multi-factor point confidence ($C \in [0, 1]$) and categorical scene coverage ratios. | `src/accuracy/` |
| **Digital Twin** | `CesiumDigitalTwin` | Mission flight replay, categorical layer toggles, 4-tier uncertainty overlay, building metric inspector. | CesiumJS, HTML5 / Vanilla JS |

---

## Strict Telemetry Provenance Rules

1. **Explicit Provenance Modes:**
   - `REAL`: Recorded from physical UAV hardware (e.g. DJI, PX4, ArduPilot telemetry logs).
   - `SIMULATED`: Synthetically generated from known physics/simulation environments (e.g. AirSim, Gazebo, OpenCV).
   - `ESTIMATED`: Derived purely from visual odometry when telemetry sensors are absent.
2. **No Silent Hardcoded GPS:**
   The system never falls back to an unverified default coordinate (e.g. `(12.9716, 77.5946, 900.0)`). When GPS is missing, the pipeline enters `LOCAL_METRIC` mode, reporting:
   > *"Georeferencing unavailable — operating in Local Metric Mode."*

---

## Multi-Dataset Validation Strategy

| Benchmark Dataset | Sensor Modalities | Target Evaluation Metric | Role in Pipeline |
|---|---|---|---|
| **Zurich Urban MAV** | High-res video, GPS, IMU, ground truth | Urban UAV reconstruction, geo-accuracy, building volumetrics | **Primary Urban Benchmark** |
| **UZH-FPV** | High-rate IMU, camera, Leica laser tracker | Absolute Trajectory Error (ATE RMSE), Relative Pose Error (RPE) | **VIO / Trajectory Benchmark** |
| **3DAeroRelief** | Low-cost UAV video, dense SfM/MVS reference | Single-pass post-disaster structural reconstruction, damage mapping | **Disaster Scene Benchmark** |
| **AirSim / Synthetic** | Perfect ground truth mesh, depth, trajectory, IMU | Controlled ablation curves under GPS noise ($\pm 1\text{m}, \pm 5\text{m}$), IMU drift, blur | **Controlled Robustness Testing** |
| **ETH3D (Delivery Area)**| Multi-view DSLR, laser-scanned ground truth | Generic multi-view geometry sanity check (25.7 MP) | **Baseline Geometry Verification** |
