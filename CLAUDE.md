# CLAUDE.md — Project Context for Implementation

This file is the standing context for whichever coding agent (Claude Code or similar)
implements this project. Read PRD.md, ARCHITECTURE.md, TECH_STACK.md, and ROADMAP.md first.

## Who's building this

One person, solo, on a laptop with an RTX 3050 (6GB VRAM), 16GB RAM, i7-13700HX. No team
to split work across. No fixed deadline — the project proceeds phase by phase, and each
phase must be fully working and demoable before the next one starts.

## Hard constraints — do not violate

1. **Never make the pipeline depend on VGGT (or any similarly license-restricted model)
   as the only geometry source.** COLMAP is the default path. Any AI geometry model goes
   behind the `estimate_geometry()` interface described in ARCHITECTURE.md, as an
   optional/swappable addition — never a hard dependency.
2. **Don't pick model checkpoints or pipeline stages that assume more than 6GB VRAM**
   without an explicit CPU or cloud-GPU fallback path.
3. **Don't build the frontend before the CV pipeline works.** Phase order in ROADMAP.md
   is deliberate — a pretty viewer with no real reconstruction behind it is worse than a
   working reconstruction with no viewer yet.
4. **Don't process every frame of a raw video.** Always run frame quality filtering first
   (Phase 1) — this is a stated requirement, not an optimization to skip for a "quick
   demo."
5. **Don't present raw model output as ground truth.** Every output should be accompanied
   by the confidence/coverage information once Phase 6 exists — and until then, be
   explicit in any interim demo that confidence reporting isn't built yet, rather than
   implying the model is more trustworthy than it is.

## Working style for this project

- One phase at a time, matching ROADMAP.md's "Definition of done" for each phase.
- When a phase's definition of done is met, stop and confirm before starting the next —
  don't cascade into the next phase automatically.
- Prefer well-established libraries (COLMAP, Open3D, OpenCV) over custom reimplementation
  wherever one exists and fits the hardware constraint.
- Keep the AI geometry module (VGGT or otherwise) genuinely swappable — write it as a
  small, isolated interface, not scattered through the pipeline.

## What "done" looks like for the core build (Phases 0–8)

A single command (or short script sequence) that takes a drone video + GPS/flight
metadata, and produces:
1. A filtered, quality-checked, semantically-segmented frame set
2. A georeferenced, metrically-scaled, class-tagged textured mesh (.obj/.glb) and point
   cloud (.ply)
3. DSM/DTM and orthomosaic exports (GeoTIFF)
4. A confidence/coverage report, broken down by region and semantic class
5. A CesiumJS-based browser viewer: measurable, with class-layer toggles and a confidence
   overlay

Everything beyond that (VGGT, 3D Gaussian Splatting, cloud GPU tiering — Phases 9–10) is
explicitly optional and should never block or complicate the core build.
