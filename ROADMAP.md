# ROADMAP — SIH26158 Drone 3D Reconstruction

**No fixed deadline. Phase-gated, not date-gated.** Each phase must produce something
demoable before starting the next — never run more than one phase "in progress" at once.

---

### Phase 0 — Feasibility Harness
**Goal:** know your system's real limits before investing in the full build.
- GPU capability check (VRAM, CUDA availability, what model sizes are realistic)
- Synthetic GPS-noise scale-recovery test — quantify expected metric-scale error
- Single-pass coverage estimate — quantify % of a scene realistically unobserved from
  one flight path geometry
- **Definition of done:** a short report (numbers + one plot) you can quote in a pitch,
  e.g. "expected scale error ~X%, ~Y% of scene surface unobserved in single pass."

### Phase 1 — Frame Extraction, Quality Filtering & Semantic Segmentation
**Goal:** turn a raw video into a clean, minimal, class-labeled frame set.
- Extract frames at a controlled interval
- Blur detection (Laplacian variance threshold)
- Near-duplicate detection (perceptual hash)
- Coverage check (ensure frames span the full flight path)
- Semantic segmentation per keyframe (UAVid's 8 classes: Building, Road, Tree, Low
  vegetation, Moving car, Static car, Human, Background clutter)
- Dynamic classes (Moving car, Human) masked out before reconstruction
- **Definition of done:** feed in a UAVid clip, get out a filtered frame folder with a
  visible before/after count (e.g. "9,000 → 420 frames") plus a per-frame segmentation
  mask for each retained frame.

### Phase 2 — COLMAP Baseline Pipeline
**Goal:** the safety-net, fully working reconstruction path.
- Frames → COLMAP feature detection → matching → sparse SfM → dense MVS → Poisson mesh
- **Definition of done:** a real .ply/.obj output from a real test video, viewable in
  any generic 3D viewer (e.g. MeshLab) as a sanity check.

### Phase 3 — Scale + Geo Alignment
**Goal:** make the model metrically meaningful and georeferenced.
- GPS/altitude-derived scale factor
- ENU coordinate conversion → lat/lon/altitude
- **Definition of done:** model coordinates map to real-world GPS positions; scale
  validated against a known object dimension or ETH3D ground truth.

### Phase 4 — Web Viewer (MVP)
**Goal:** make Phases 1–3 demoable as a complete product, not a folder of files.
- Load .glb/.obj into a quick viewer (Three.js or Streamlit widget — speed over polish)
- One measurement tool: click two points → distance
- **Definition of done:** open a browser, load a model, click two points, see a distance
  number that's roughly correct.

### Phase 5 — Depth Fusion (Density Upgrade)
**Goal:** denser, better point cloud without VGGT's VRAM cost.
- Depth Anything V2 per keyframe → fuse with COLMAP sparse points
- Open3D outlier removal on the fused cloud
- **Definition of done:** visibly denser point cloud than Phase 2 alone, same or better
  mesh quality.

### Phase 6 — Confidence / Coverage Reporting
**Goal:** be honest about what the model doesn't know — done rigorously, not as an
afterthought.
- Per-region observation count, reprojection error, depth consistency
- Break down by semantic class as well as by region (e.g. "buildings: 91% confident,
  vegetation: 62% confident")
- Visual confidence overlay (high/medium/low) in the viewer
- **Definition of done:** a judge can toggle a "confidence" view and see which parts of
  the model — and which classes — are trustworthy vs. guessed/interpolated.

### Phase 7 — Class Tagging + DSM/DTM + Orthomosaic Exports
**Goal:** answer the PS's five literal output categories directly, and add the standard
GIS deliverables several competing repos already include.
- Carry per-frame semantic labels (Phase 1) onto point cloud/mesh regions via projection
- Export DSM/DTM (GeoTIFF) by gridding the georeferenced point cloud
- Export an orthomosaic (GeoTIFF) by stitching frames using camera poses from COLMAP
- **Definition of done:** the viewer can isolate/toggle "buildings only," "roads only,"
  "vegetation only"; DSM/DTM and orthomosaic files open correctly in QGIS or similar.

### Phase 8 — CesiumJS Viewer Upgrade
**Goal:** replace the MVP viewer with a georeferenced, GIS-grade one.
- Migrate model + class layers + confidence overlay + measurement tool into CesiumJS
- Load DSM/DTM and orthomosaic as additional map layers
- **Definition of done:** a single CesiumJS page showing the georeferenced model, with
  working layer toggles, confidence overlay, and measurement tool — this becomes the
  actual demo interface.

### Phase 9 — [Stretch] VGGT Integration
**Goal:** faster geometry estimation, if hardware/compute allows.
- Implement VGGT behind the same `estimate_geometry()` interface as COLMAP
- Test locally first; fall back to Colab/Kaggle T4 if 6GB VRAM is insufficient for
  realistic frame counts
- Explicitly address the military-use license restriction in any pitch material
- **Definition of done:** VGGT path produces comparable output to COLMAP path on a test
  clip, with COLMAP still fully functional as fallback.

### Phase 10 — [Stretch] 3D Gaussian Splatting Visualization
**Goal:** the "wow factor" visualization layer, on top of an already-complete system.
- Train a Gaussian Splat from the same frame set (gsplat / Nerfstudio Splatfacto)
- Add as an alternate view mode in CesiumJS or a companion viewer (not a replacement for
  the measurable mesh)
- **Definition of done:** toggle between "measurable mesh" and "photorealistic splat"
  views in the same demo flow.

---

## Pitch/Demo Narrative — Deferred

Per current scope decision, the pitch narrative (problem → innovation → architecture →
feasibility → impact slide structure) is being planned separately from the technical
build and picked up later. Don't let it block Phase 0–8 progress.
