# ARCHITECTURE — SIH26158 Drone 3D Reconstruction

## Design Principle

**Each tool for what it's best at.** Don't pick one technique (pure AI, pure photogrammetry,
pure NeRF/3DGS) — combine them, with a classical, well-understood method (COLMAP) as the
trustworthy backbone and a swappable AI module layered on top for speed/density, never as
a single point of failure.

## High-Level Pipeline

```
DRONE VIDEO (+ GPS + flight metadata)
        │
        ▼
Frame Extraction (OpenCV, interval-based)
        │
        ▼
Frame Quality Filter
  - Blur detection (Laplacian variance)
  - Near-duplicate detection (perceptual hash / SSIM)
  - Coverage check (ensure full flight path represented)
        │
        ▼
Semantic Segmentation Pass (per keyframe)
  - Classes: Building, Road, Tree, Low vegetation, Moving car, Static car, Human, Background
  - Dynamic classes (Moving car, Human) → masked out before reconstruction
  - Static classes (Building, Road, Tree/vegetation) → carried forward as point/mesh tags
        │
        ▼
   ┌────────────────────┐
   │  COLMAP (baseline)  │──── feature detection → matching → SfM → sparse cloud
   └─────────┬──────────┘
             │
             ▼
   Optional: Depth Anything V2 monocular depth per keyframe
             │
             ▼
   Depth + Sparse Point Fusion → Dense Point Cloud
             │
             ▼
   Outlier Removal (statistical + radius filtering, Open3D)
             │
             ▼
   Scale + Geo Alignment (GPS/altitude-derived scale factor, ENU coordinate conversion)
             │
        ┌────┴────┐
        ▼         ▼
   Mesh (Poisson  Confidence/Coverage Report
   or TSDF,       (observation count, reprojection error,
   class-tagged)   % scene unseen, per-class breakdown)
        │
        ▼
   Texture Mapping (project original frames onto mesh)
        │
        ▼
   ┌─────────────┬─────────────┬──────────────┐
   ▼             ▼             ▼              ▼
 Point Cloud   Textured Mesh  DSM/DTM       Orthomosaic
 (.ply,        (.obj/.glb,    (GeoTIFF,     (GeoTIFF,
 class-tagged) class-tagged)  gridded from  stitched from
                              point cloud)  frames+poses)
   └─────────────┴─────────────┴──────────────┘
                       │
                       ▼
   Web Viewer (CesiumJS — georeferenced 3D Tiles/terrain)
     - Load model with class-based layer toggles
     - Click-to-measure (distance between two points)
     - Confidence overlay toggle
        │
        ▼
   [STRETCH] VGGT swap-in behind a Geometry Module interface
   [STRETCH] 3D Gaussian Splatting visualization layer
   [STRETCH] Cloud GPU tiering (Colab/Kaggle T4) for VGGT-heavy runs
```

## Component Responsibilities

| Component | Responsibility | Library/Tool |
|---|---|---|
| Video Decoder | Extract frames at controlled interval | OpenCV / FFmpeg |
| Frame Quality Filter | Blur, duplicate, coverage filtering | OpenCV (Laplacian), imagehash |
| Semantic Segmentation | Classify buildings/roads/vegetation/terrain/dynamic objects per frame | UAVid-class segmentation model (SegFormer or similar) |
| Object Masking | Remove dynamic objects (moving car, human) before reconstruction | Output of Semantic Segmentation, no separate model needed |
| SfM/MVS Core | Camera poses, sparse + dense point cloud | COLMAP |
| Depth Module | Dense monocular depth per frame | Depth Anything V2 (fits 6GB VRAM) |
| Point Fusion | Merge COLMAP sparse + depth-derived dense points | Custom (NumPy/Open3D) |
| Outlier Removal | Clean point cloud | Open3D |
| Scale/Geo Alignment | GPS/altitude scale factor, ENU conversion | Custom + pyproj |
| Class Tagging | Carry per-frame semantic labels onto point cloud/mesh regions | Custom (nearest-frame projection) |
| Mesh Reconstruction | Point cloud → surface mesh | Open3D (Poisson / TSDF) |
| Texture Mapping | Project frame textures onto mesh | Open3D / custom visibility calc |
| DSM/DTM Export | Grid the point cloud into elevation rasters | GDAL / rasterio |
| Orthomosaic Export | Stitch top-down 2D map from frames + poses | OpenCV / custom |
| Confidence Module | Score density/reprojection error per region, incl. per-class | Custom |
| Web Viewer | Georeferenced interactive display + measurement + layer toggles | CesiumJS |

## The Swappable AI Geometry Module (Practicability requirement)

VGGT's license permits commercial use but explicitly **excludes military applications**,
and only a separate, application-gated commercial checkpoint is licensed at all — the
original checkpoint remains non-commercial. Since this PS explicitly lists military
reconnaissance as an application, VGGT must never be presented as an unquestioned
production dependency.

**Design contract:** any AI geometry estimator (VGGT or otherwise) sits behind a single
interface (`estimate_geometry(frames) -> poses, depth, points`). COLMAP's SfM/MVS output
satisfies the same interface and is the default/fallback path. Swapping models later means
implementing the interface, not rewriting the pipeline.

## Hardware-Driven Decisions

RTX 3050 6GB is tight for VGGT (memory-heavy across many frames simultaneously) but
comfortable for:
- COLMAP sparse reconstruction (CPU-tolerant, GPU accelerates feature matching)
- COLMAP dense MVS (needs CUDA — RTX 3050 qualifies, just slower on large frame counts)
- Depth Anything V2 (lightweight, designed to run on consumer GPUs)

**Decision:** Depth Anything V2 is the primary AI depth-fusion path for MVP. VGGT is a
stretch-phase addition, gated on either accepting slower/limited runs locally or using a
free-tier cloud GPU (Colab/Kaggle T4) for those specific runs.

## Georeferencing

Convert local reconstruction coordinates → ENU (East-North-Up) frame anchored at the
flight's GPS origin → standard lat/lon/altitude. This is the standard geodesy approach for
this exact conversion (rather than an ad-hoc scale-and-shift).
