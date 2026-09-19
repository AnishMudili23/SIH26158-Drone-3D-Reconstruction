# PRD — SIH26158: Single-Pass Drone Video to Accurate 3D Model Generation

**Problem Statement:** SIH26158, NTRO, Theme: Robotics & Drones, Category: Software
**Team status:** Same team as the SIH multimodal RAG project (internal SIH cleared). This is the current active PS.
**Builder:** Solo build. No fixed deadline — phase-gated, not date-gated.
**Hardware:** HP Omen — RTX 3050 6GB VRAM, 16GB RAM, i7-13700HX.

---

## 1. Problem Summary

Generate an accurate, textured, **georeferenced** 3D model of a scene (terrain, buildings,
roads, vegetation) from a **single drone flight pass video** — no multi-pass photogrammetry,
no dense Ground Control Points (GCPs).

**Why it's hard:** limited viewing angles, motion blur/compression artifacts, variable
lighting, dynamic objects, GPS noise, occluded surfaces, and the need for metric accuracy
without GCPs — all while ideally running near real-time.

**Important clarification:** "single pass" ≠ "single image." A flight still yields hundreds
of frames with parallax — this is still multi-view reconstruction, just from one continuous
trajectory instead of separately planned passes.

## 2. Official Inputs (per NTRO PS text)

- **Mandatory:** drone video (1080p/4K), GPS coordinates, flight metadata
- **Optional:** IMU data, barometric altitude, camera intrinsics, RTK/PPK corrections

## 3. Official Outputs (per PS)

- Terrain and structures
- Building facades and rooftops
- Roads and infrastructure
- Vegetation and obstacles
- Textured 3D mesh or point cloud, suitable for visualization, measurement, and analysis

**Design commitment:** these five items are read literally, not as one undifferentiated
mesh. The pipeline includes a semantic segmentation pass so the point cloud/mesh is
class-tagged (terrain, building, road, vegetation) and each class can be isolated/toggled
in the viewer — not just implied by an unlabeled combined model. See Section 9.

**Note:** NTRO's official "Desired Output" and "Evaluation Criteria" tables are still
unpublished (placeholder text as of last check). Section 5 below defines our own working
targets so the project has something concrete to build and test against. Re-check the
official portal periodically — this should update once NTRO publishes it.

## 4. Judging Rubric Alignment (SIH standard 9-axis rubric)

The project is explicitly designed to score on: Novelty, Complexity, Clarity, Feasibility,
Practicability, Sustainability, Scale of Impact, User Experience, Future Work Potential.

Design decisions this drives:
- **Novelty differentiator:** honest confidence/coverage reporting as a first-class feature,
  not an afterthought (most competing approaches treat this as a stretch goal — we don't).
- **Feasibility:** a quantified Phase 0 feasibility harness (real numbers on GPU capability,
  scale-recovery error, single-pass coverage gaps) instead of assumed feasibility.
- **Practicability/Sustainability:** offline-capable, no paid API dependency, AI geometry
  module is swappable (addresses the VGGT military-use license restriction head-on).
- **Future Work Potential:** stretch phases (VGGT swap-in, 3D Gaussian Splatting, cloud-GPU
  tiering) double as the explicit "where this goes next" story for judges.

## 5. Our Working Success Targets (self-defined, pending NTRO's real rubric)

- Reconstruct a scene from a single continuous flight video with no manual GCP placement.
- Metric scale error target: within ~5% using GPS+altitude alone (tighter if IMU available)
  — validated against ETH3D ground truth and/or known real-world object dimensions.
- Report honest coverage: % of scene observed vs. occluded/unseen in the single pass.
- Output formats: point cloud (.ply), textured mesh (.obj/.glb), DSM/DTM (GeoTIFF), an
  orthomosaic (GeoTIFF), all viewable + measurable in a browser, with mesh/point-cloud
  regions class-tagged (terrain/building/road/vegetation).
- Processing time: not a hard real-time requirement for MVP — optimize for correctness
  first, speed later (stretch goal only).

## 6. Explicit Non-Goals (MVP scope)

- No training a 3D reconstruction model from scratch.
- No reliance on VGGT's original non-commercial checkpoint or the commercial checkpoint's
  military-use-restricted terms for anything beyond local prototyping — production path
  must have a COLMAP-only fallback.
- No real-time (<1 min) processing target for MVP.
- No dense GCP requirement anywhere in the pipeline.
- No multi-person team coordination — plan assumes solo execution.

## 7. Applications to Reference in the Pitch (from PS text)

Border/strategic area mapping, disaster damage assessment, urban planning, infrastructure
inspection, construction progress monitoring, archaeological documentation, digital twin
generation, military reconnaissance and mission planning.

## 8. Datasets

- **UAVid** (https://uavid.nl/) — realistic raw 4K oblique drone footage for testing frame
  extraction, keyframe selection, and dynamic-object segmentation. *Not* a reconstruction
  ground-truth dataset (it's a semantic segmentation dataset — no camera poses, no 3D GT).
- **ETH3D** (https://eth3d.ethz.ch/datasets) — multi-view images + camera info + laser-scanner
  ground-truth 3D, used to validate reconstruction accuracy (not drone footage, but valid
  for testing the reconstruction math itself).
- **NTRO's real dataset** — expected at the hackathon stage; UAVid/ETH3D are for pre-build
  development and testing only.
- UAVid's own 8 semantic classes (Building, Road, Tree, Low vegetation, Moving car,
  Static car, Human, Background clutter) are reused directly as the semantic segmentation
  training/reference classes in Section 9 — not just for frame-quality testing.

## 9. Competitive Gap-Closing Additions

A review of several public repos targeting this same PS found the core architecture
(COLMAP + AI depth + georeferencing + viewer) is now common ground, not a differentiator.
Four additions close real gaps against the PS's literal wording and the stronger public
attempts, without requiring new reconstruction techniques:

1. **Semantic segmentation pass** — classify buildings/roads/vegetation/terrain (reusing
   UAVid's 8 classes) and tag point-cloud/mesh regions by class, so the PS's five literal
   output categories are genuinely separable/toggleable, not just implied.
2. **DSM/DTM export** (Digital Surface Model / Digital Terrain Model, GeoTIFF) — a
   projection/gridding operation on the already-georeferenced point cloud, not new
   reconstruction work. Standard GIS deliverable several competing repos already include.
3. **Orthomosaic export** (stitched top-down 2D map, GeoTIFF) — derivable from the existing
   frame set + camera poses.
4. **CesiumJS instead of generic Three.js for the viewer** — purpose-built for georeferenced
   3D Tiles/terrain/GIS context; reads as a more "serious NTRO tool" than a generic model
   viewer, at the cost of a steeper learning curve.

These are folded into ROADMAP.md as explicit phases, not left as vague ambitions.
