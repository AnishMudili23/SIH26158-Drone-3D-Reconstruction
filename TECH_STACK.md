# TECH STACK — SIH26158 Drone 3D Reconstruction

**Constraint context:** solo builder, RTX 3050 6GB VRAM, 16GB RAM, i7-13700HX, no deadline.
Every choice below is picked to actually run on this machine, not on an assumed workstation.

## Core Pipeline

| Purpose | Choice | Notes |
|---|---|---|
| Language | Python 3.10+ | Matches COLMAP/Open3D/PyTorch ecosystem |
| Video I/O | OpenCV | Frame extraction, blur detection (Laplacian variance) |
| Near-duplicate detection | `imagehash` (perceptual hashing) | Cheap, no GPU needed |
| Semantic segmentation | SegFormer (or similar) fine-tuned/mapped to UAVid's 8 classes | Building/Road/Tree/Low vegetation/Moving car/Static car/Human/Background; also replaces the separate dynamic-object masking step |
| DSM/DTM generation | GDAL / rasterio | Grids the georeferenced point cloud into elevation rasters (GeoTIFF) |
| Orthomosaic generation | OpenCV (homography stitching) | Uses existing frames + camera poses from COLMAP |
| SfM / MVS | COLMAP | CUDA-accelerated feature matching + dense stereo; CPU fallback exists but is slow |
| Monocular depth | Depth Anything V2 (small/base checkpoint) | Fits comfortably in 6GB; avoid the largest checkpoint |
| Point cloud processing | Open3D | Outlier removal, normals, Poisson/TSDF meshing |
| Geo conversion | `pyproj` | ENU ↔ lat/lon/altitude conversion |
| Mesh format | .obj / .glb | .glb preferred for web viewer compatibility |

## Feasibility Harness (Phase 0)

| Purpose | Choice |
|---|---|
| GPU capability check | PyTorch (CUDA build) — `torch.cuda.get_device_properties` |
| Synthetic GPS-noise scale test | NumPy + matplotlib for visualization |
| Coverage estimation | Custom script using sample flight-path geometry |

## Web Viewer

| Purpose | Choice | Notes |
|---|---|---|
| 3D rendering (final) | CesiumJS | Purpose-built for georeferenced 3D Tiles/terrain — reads as a serious GIS/NTRO tool, not a generic model viewer. Steeper learning curve than Three.js — budget real time for this. |
| Fast interim viewer (Phase 4 MVP) | Streamlit + a point-cloud/mesh viewer widget, or plain Three.js | Get *something* viewable and measurable fast; migrate to CesiumJS once layer-toggle/georeferencing needs justify the switch (Phase 9) |
| Measurement tool | Raycasting on click (Three.js first, CesiumJS later) | Distance between two clicked points |

## Stretch Phase Additions

| Purpose | Choice | Notes |
|---|---|---|
| AI feed-forward geometry | VGGT | Gate behind the swappable interface; local runs will be slow/limited on 6GB, consider cloud GPU for full runs |
| Fast photorealistic viz | 3D Gaussian Splatting (gsplat / Nerfstudio Splatfacto) | Visualization layer only, not the accuracy-bearing output |
| Cloud GPU (if needed) | Google Colab / Kaggle free-tier T4 | For VGGT-heavy runs only; local pipeline should never *require* this |

## Explicitly Avoided for MVP

- NeRF (Instant-NGP etc.) — training cost too high for solo/no-deadline-but-still-limited-time build, low return over Depth Anything V2 + COLMAP for this PS's accuracy requirement.
- VGGT as the *only* geometry source — license risk + VRAM risk on this hardware.
- Any cloud-dependent production path — PS context (disaster response, defense) implies offline capability matters.

## Version Pinning Note

Pin exact versions once you start `pip install`-ing (COLMAP via conda-forge or prebuilt
binary is usually easier than building from source on Windows). Record final pinned
versions in this file once Phase 0/1 environment setup is done.
