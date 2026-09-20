# ROADMAP — SIH26158 Sensor-Fused 4D Drone Reconstruction

**Continuous Improvement & Sensor-Fused Engineering Roadmap.**  
Phases 0–8 established the baseline end-to-end photogrammetric and GIS pipeline. The current evolution pivots from a basic "Video to 3D" prototype to an **offline-capable, sensor-fused, uncertainty-aware 4D reconstruction engine**.

---

## Baseline Foundation (Completed & Verified)

- [x] **Phase 0 — Feasibility Harness:** Scale-recovery sensitivity analysis, synthetic GPS-noise bounds, and single-pass geometric coverage constraints.
- [x] **Phase 1 — Keyframe Extraction & Semantic Masking:** Laplacian blur filter, perceptual-hash duplicate filter, SegFormer UAVid-mapped semantic masks, and dynamic-object masking (moving cars/humans).
- [x] **Phase 2 — COLMAP Incremental SfM Core:** Feature detection, sequential matching, camera calibration parsing, and sparse point cloud triangulation.
- [x] **Phase 3 — Scale & Georeference Similarity Alignment:** Umeyama SVD similarity alignment, ENU cartesian conversion, and camera pose rederivation.
- [x] **Phase 4 — ASPRS 1.4 Point Cloud Export:** Point Format 7 (`.las` / `.laz`) with 8-bit classification codes, 16-bit RGB, intensity, and WGS84/UTM GeoKey VLRs.
- [x] **Phase 5 — Dense Depth Fusion:** Depth Anything V2 monocular depth estimation, affine scale/shift alignment, and statistical/radius outlier filtering.
- [x] **Phase 6 — Confidence Tiers & Volumetric Metrics:** Track-length and reprojection confidence grading, DSM/DTM height differential, above-ground structure volume ($m^3$), and footprint area ($m^2$).
- [x] **Phase 7 — GIS Deliverables:** Digital Surface Model (DSM), Digital Terrain Model (DTM), and 2D Orthomosaic GeoTIFF exports.
- [x] **Phase 8 — CesiumJS 3D GIS Viewer:** Interactive georeferenced browser viewer with class layer toggles, confidence overlay, dataset switcher, and click-to-measure tool.
- [x] **Regression Test Suite:** 36/36 unit tests passing across all components.

---

## Strategic Evolution: Sensor-Fused & Uncertainty-Aware System

### Phase A — Sensor Synchronization & Telemetry Data Model
**Goal:** Ingest multi-sensor drone telemetry with explicit provenance and temporal synchronization.
- Implement `FlightSession` schema capturing video frames, camera calibration (focal length, principal point, radial/tangential distortion, rolling shutter), GPS fixes, 6-DoF IMU (accel/gyro), and barometric altitude.
- Sub-millisecond sensor timestamp alignment via linear/cubic spline interpolation.
- Enforce strict telemetry provenance (`REAL`, `SIMULATED`, `ESTIMATED`). Eliminate silent artificial default coordinates; fall back to `LOCAL_METRIC` mode if GPS is absent.
- Implement 6-DoF Extended Kalman Filter (EKF) propagating IMU dynamics with GPS/barometer corrections to output continuous flight trajectories with covariance bounds.

### Phase B — Intelligent Adaptive Keyframe Engine
**Goal:** Transition from fixed-interval frame extraction to adaptive geometric frame selection.
- Compute multi-criteria frame quality: sharpness (modified Laplacian), exposure balance, baseline parallax from EKF trajectory, and mutual feature overlap.
- Target optimal 60%–80% spatial overlap while minimizing computational redundancy.
- Dynamically scale frame density during aggressive maneuvers vs straight cruise.

### Phase C — Robust Trajectory & Geo-Constrained BA
**Goal:** Constrain visual bundle adjustment using metric telemetry priors.
- Feed continuous EKF flight trajectory as position/orientation priors into bundle adjustment.
- Mitigate scale drift and non-linear trajectory bend on long single-pass flight corridors.

### Phase D — Multi-View Depth Consistency & AI Prior Fusion
**Goal:** Treat AI depth strictly as an uncertainty-weighted prior verified by geometric consensus.
- Cross-camera forward-backward depth reprojection across adjacent keyframe poses.
- Rejection of depth predictions with $>5\%$ relative reprojection discrepancy.
- Confidence-weighted blending of MVS dense depth and verified AI depth priors.

### Phase E — Dedicated Metric Accuracy & Uncertainty Subsystem (`src/accuracy/`)
**Goal:** Rigorous, defensible quantification of reconstruction quality.
- Absolute Trajectory Error (ATE RMSE) and Relative Pose Error (RPE) against laser/RTK ground truth.
- Scale error % ($|s_{est} - s_{gt}| / s_{gt}$) and horizontal/vertical geolocation RMSE.
- Categorical surface coverage ratios: Terrain %, Roofs %, Facades %, Vegetation %, Roads %, with explicit accounting for unobserved/occluded surfaces.
- Multi-factor point uncertainty $C \in [0, 1]$ combining ray intersection angle, reprojection error, depth consensus, and image quality.

### Phase F — Class-Specific Surface Reconstruction & UV Texture Atlas
**Goal:** Specialized geometric representation and true photo-textured mesh assets.
- Terrain representation via DTM elevation grid; architectural structures via Poisson/alpha-shape surface mesh; vegetation via point cloud/splat representation.
- Triangle-camera visibility raycasting, optimal view angle selection (penalizing glancing angles), and UV texture atlas packing (`mesh.glb` + texture maps).

### Phase G — Operational Cesium Digital Twin & Mission Replay
**Goal:** Turn the viewer into a mission-grade intelligence and GIS tool.
- Mission flight replay slider: scrub flight time to inspect drone position, camera frustum, and reconstructed scene.
- Categorical layer toggles: Buildings, Roads, Terrain, Vegetation, Vehicles.
- 4-Tier uncertainty heatmap overlay: Green (High), Yellow (Medium), Red (Low), Gray (Unobserved).
- Interactive structure inspection: click building to view height, footprint area, and estimated volume.

### Phase H — Multi-Dataset Benchmark Harness & Controlled Ablation
**Goal:** Validate across diverse real-world benchmarks and controlled stress conditions.
- **Zurich Urban MAV:** Primary urban UAV reconstruction benchmark with synchronized GPS/IMU and ground truth.
- **UZH-FPV:** High-rate IMU and Leica laser-tracker trajectory validation.
- **3DAeroRelief:** Single-pass post-disaster structural reconstruction.
- **AirSim / Synthetic Ablation:** Controlled degradation curves under injected GPS noise ($\pm 1\text{m}, \pm 5\text{m}$), IMU drift, blur, and altitude variations.
