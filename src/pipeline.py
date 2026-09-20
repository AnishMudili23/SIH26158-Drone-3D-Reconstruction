"""
SIH26158 — Unified End-to-End Drone 3D Reconstruction Pipeline Runner
(Fulfills CLAUDE.md: "A single command (or short script sequence) that takes a drone
video + GPS/flight metadata, and produces filtered frames, georeferenced textured mesh,
classified point clouds (.las/.laz), DSM/DTM/orthomosaic GeoTIFFs, confidence report,
and CesiumJS viewer data").

CLI Usage:
  python -m src.pipeline --input <video_or_image_folder> --gps-log <path_to_gps_csv_or_json> --output-dir <output_dir>
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
import cv2
import numpy as np

# Ensure src/ is on path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from common.geometry_interface import CameraPose, GeometryEstimate
from reconstruction.colmap_backend import (
    ColmapBackend,
    read_sparse_text_model,
    _quat_to_rotmat,
    _camera_intrinsics,
)
from pointcloud.outlier_removal import remove_statistical_outliers
from geo.scale_alignment import (
    GpsFix,
    align_geometry_to_gps,
    enu_to_gps,
    gps_fixes_to_enu,
    lla_to_enu,
)
from reconstruction.geo_constrained_ba import refine_poses_with_gps_priors
from exports.texture_mapper import CameraView, UVTextureMapper
from exports.class_tagging import tag_points_by_class, tags_to_class_names
from exports.las_export import export_point_cloud_to_las
from exports.dsm_dtm import export_dsm_dtm, utm_epsg_for_lonlat
from exports.orthomosaic import (
    build_orthomosaic,
    estimate_ground_z_ref,
)
from confidence.confidence_report import (
    compute_confidence_tiers,
    per_class_confidence_breakdown,
)
from telemetry.flight_session import FlightSession
from frame_processing.adaptive_keyframes import AdaptiveKeyframeEngine


def run_pipeline(
    input_path: str | Path,
    output_dir: str | Path,
    gps_log_path: str | Path | None = None,
    telemetry_path: str | Path | None = None,
    allow_simulated_gps: bool = False,
    default_origin: tuple[float, float, float] = (12.9716, 77.5946, 900.0),
    run_dense: bool = False,
    reuse_sparse: str | bool = False,
    use_adaptive_keyframes: bool = False,
    run_geo_constrained_ba: bool = False,
    geo_ba_gps_weight: float = 1.0,
    run_uv_texture_mapping: bool = False,
) -> dict:
    """Executes the full SIH26158 3D reconstruction pipeline end-to-end.

    Parameters
    ----------
    input_path : str | Path
        Directory of images or video file path.
    output_dir : str | Path
        Target root directory for all deliverables.
    gps_log_path : str | Path | None
        Legacy path to a raw GPS log (CSV or JSON). Prefer `telemetry_path`.
    telemetry_path : str | Path | None
        Path to a `telemetry.FlightSession` JSON (real GPS/IMU/barometer, camera
        calibration, explicit provenance). Preferred over `gps_log_path`.
    allow_simulated_gps : bool
        Explicit opt-in to fabricate GPS fixes anchored at `default_origin` when no
        real telemetry is supplied. Per ROADMAP.md Phase A's strict provenance rule,
        this is OFF by default — with no real GPS and this flag unset, the pipeline
        runs in LOCAL_METRIC mode (arbitrary-scale, ungeoreferenced output) rather
        than silently inventing coordinates.
    default_origin : tuple[float, float, float]
        (lat, lon, alt_m) used only when `allow_simulated_gps=True`.
    run_dense : bool
        Whether to run dense Poisson MVS reconstruction (slower, GPU intensive).
    use_adaptive_keyframes : bool
        Use the multi-criteria AdaptiveKeyframeEngine (sharpness, exposure, overlap)
        instead of fixed-interval extraction + blur/duplicate filtering, when the
        input is a video.
    run_geo_constrained_ba : bool
        Run Phase C's pose-only geo-constrained refinement (reprojection + GPS-prior
        joint optimization) after GPS alignment, as a diagnostic trajectory
        comparison. Written to `refined_trajectory.json` alongside the other
        deliverables rather than overwriting the primary georeferenced outputs,
        since it only refines camera positions (not points or orientation) — see
        `src/reconstruction/geo_constrained_ba.py` for the documented scope limit.

    Returns
    -------
    dict
        Summary of deliverables and metric validation stats.
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = output_dir / "frames"
    masks_dir = output_dir / "masks"
    reconstruction_dir = output_dir / "reconstruction"
    deliverables_dir = output_dir / "deliverables"
    viewer_dir = output_dir / "viewer_data"

    for d in (frames_dir, masks_dir, reconstruction_dir, deliverables_dir, viewer_dir):
        d.mkdir(parents=True, exist_ok=True)

    print("\n========================================================")
    print("  SIH26158 Single-Pass Drone 3D Reconstruction Pipeline")
    print("========================================================\n")

    # ---------------------------------------------------------
    # Stage 1: Frame Acquisition / Ingestion
    # ---------------------------------------------------------
    print("[Stage 1/7] Ingesting and filtering frames...")
    frame_paths: list[Path] = []
    if input_path.is_dir():
        frame_paths = sorted(
            p for p in input_path.iterdir()
            if p.suffix.lower() in (".jpg", ".jpeg", ".png")
        )
        print(f"  Ingested {len(frame_paths)} frames from directory: {input_path}")
    elif input_path.is_file() and input_path.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv"):
        if use_adaptive_keyframes:
            print(f"  Adaptive keyframe selection (sharpness/exposure/overlap) from video: {input_path}")
            kept_dir = output_dir / "phase1" / "kept_frames"
            kept_dir.mkdir(parents=True, exist_ok=True)
            cap = cv2.VideoCapture(str(input_path))
            src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            candidate_stride = max(1, round(src_fps / 5.0))  # 5 candidate fps into the scorer
            frames, timestamps = [], []
            raw_idx = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if raw_idx % candidate_stride == 0:
                    frames.append(frame)
                    timestamps.append(raw_idx / src_fps)
                raw_idx += 1
            cap.release()
            engine = AdaptiveKeyframeEngine()
            scores = engine.select_keyframes(frames, timestamps)
            frame_paths = []
            for s in scores:
                if not s.is_selected:
                    continue
                out_path = kept_dir / f"frame_{s.frame_idx:06d}.jpg"
                cv2.imwrite(str(out_path), frames[s.frame_idx])
                frame_paths.append(out_path)
            n_rejected = sum(1 for s in scores if not s.is_selected)
            print(f"  Retained {len(frame_paths)}/{len(scores)} candidate frames "
                  f"({n_rejected} rejected: blur/exposure/insufficient baseline)")
        else:
            from frame_processing.run_phase1 import run_phase1
            print(f"  Extracting and quality-filtering keyframes from video: {input_path}")
            phase1_res = run_phase1(
                video_path=str(input_path),
                work_dir=str(output_dir / "phase1"),
                target_extract_fps=2.0,
                run_segmentation=False,
            )
            kept_dir = output_dir / "phase1" / "kept_frames"
            frame_paths = sorted(
                p for p in kept_dir.iterdir()
                if p.suffix.lower() in (".jpg", ".jpeg", ".png")
            )
            print(f"  Retained {len(frame_paths)} sharp, non-duplicate keyframes after quality filtering")
    else:
        raise ValueError(f"Unsupported input: {input_path}")

    if len(frame_paths) < 3:
        raise ValueError(f"Need at least 3 frames to reconstruct, found {len(frame_paths)}")

    # ---------------------------------------------------------
    # Stage 2: Semantic Segmentation & Masking
    # ---------------------------------------------------------
    print("\n[Stage 2/7] Generating semantic masks & dynamic object filters...")
    recon_mask_dir = None
    try:
        from frame_processing.segmentation import Segmenter, resolve_car_dynamics
        from frame_processing.masking import build_colmap_masks
        segmenter = Segmenter()
        prev_uavid = None
        class_mask_paths = []
        frame_str_paths = [str(p) for p in frame_paths]
        for p in frame_paths:
            mask_out = masks_dir / f"{p.stem}_mask.png"
            if not mask_out.exists():
                img = cv2.imread(str(p))
                if img is not None:
                    raw_uavid = segmenter.predict_uavid_mask(img)
                    resolved = resolve_car_dynamics(prev_uavid, raw_uavid)
                    prev_uavid = raw_uavid
                    cv2.imwrite(str(mask_out), resolved)
            class_mask_paths.append(str(mask_out))

        colmap_masks_dir = output_dir / "colmap_masks"
        build_colmap_masks(frame_str_paths, class_mask_paths, colmap_masks_dir)
        print(f"  Generated semantic class masks in: {masks_dir}")
        print(f"  Generated COLMAP dynamic-object masks in: {colmap_masks_dir}")
        recon_mask_dir = colmap_masks_dir
    except Exception as e:
        print(f"  [Notice] Skipping neural mask extraction ({e}); proceeding with unmasked SfM.")
        recon_mask_dir = None

    # ---------------------------------------------------------
    # Stage 3: COLMAP Sparse Structure-from-Motion
    # ---------------------------------------------------------
    print("\n[Stage 3/7] Processing COLMAP sparse reconstruction...")
    image_folder = frame_paths[0].parent
    if reuse_sparse:
        if isinstance(reuse_sparse, (str, Path)) and Path(reuse_sparse).exists():
            sparse_txt_dir = Path(reuse_sparse)
            print(f"  Reusing existing sparse reconstruction from: {sparse_txt_dir}")
        elif (reconstruction_dir / "sparse_txt" / "images.txt").exists():
            sparse_txt_dir = reconstruction_dir / "sparse_txt"
            print(f"  Reusing existing sparse reconstruction in: {sparse_txt_dir}")
        else:
            backend = ColmapBackend()
            sparse_txt_dir = backend.run_sparse_reconstruction(
                image_dir=image_folder,
                work_dir=reconstruction_dir,
                mask_dir=recon_mask_dir,
            )
    else:
        backend = ColmapBackend()
        sparse_txt_dir = backend.run_sparse_reconstruction(
            image_dir=image_folder,
            work_dir=reconstruction_dir,
            mask_dir=recon_mask_dir,
        )
    sparse_model = read_sparse_text_model(sparse_txt_dir)
    n_reg_images = len(sparse_model["images"])
    n_sparse_points = sparse_model["points_xyz"].shape[0]
    print(f"  SfM Model Loaded: {n_reg_images}/{len(frame_paths)} frames registered, {n_sparse_points} 3D points")

    poses: list[CameraPose] = []
    for image_id, img in sparse_model["images"].items():
        r = _quat_to_rotmat(*img["quat_wxyz"])
        t = np.array(img["translation"])
        k = _camera_intrinsics(sparse_model["cameras"][img["camera_id"]])
        poses.append(CameraPose(frame_path=img["name"], rotation=r, translation=t, intrinsics=k))

    # ---------------------------------------------------------
    # Stage 4: Outlier Removal & Geometry Cleanup
    # ---------------------------------------------------------
    print("\n[Stage 4/7] Cleaning sparse point cloud (outlier filtering)...")
    outlier_mask, _ = remove_statistical_outliers(sparse_model["points_xyz"], nb_neighbors=20, std_ratio=2.0)
    clean_points = sparse_model["points_xyz"][outlier_mask]
    clean_rgb = sparse_model["points_rgb"][outlier_mask]
    clean_point_ids = [pid for pid, keep in zip(sparse_model["point_ids"], outlier_mask) if keep]
    clean_track_len = sparse_model["track_len"][outlier_mask]
    clean_reproj_err = sparse_model["reprojection_error"][outlier_mask]
    print(f"  Retained {clean_points.shape[0]}/{n_sparse_points} points ({outlier_mask.mean()*100:.1f}%)")

    clean_geom = GeometryEstimate(
        poses=poses,
        points_xyz=clean_points,
        points_rgb=clean_rgb,
        points_confidence=clean_track_len,
        backend_name="colmap",
        is_metric_scale=False,
    )

    # ---------------------------------------------------------
    # Stage 5: GPS / Scale Georeferencing
    # ---------------------------------------------------------
    print("\n[Stage 5/7] Georeferencing & scale alignment...")
    gps_fixes: list[GpsFix] = []
    telemetry_provenance = "NONE"

    if telemetry_path and Path(telemetry_path).exists():
        session = FlightSession.load_json(telemetry_path)
        session.synchronize_telemetry()
        telemetry_provenance = session.provenance.value
        frames_by_name = {f.image_filename: f for f in session.frames}
        for p in frame_paths:
            f = frames_by_name.get(p.name)
            if f is not None and f.gps is not None:
                gps_fixes.append(GpsFix(p.name, f.gps.latitude, f.gps.longitude, f.gps.altitude_m))
        print(f"  Loaded FlightSession telemetry (provenance={telemetry_provenance}): "
              f"{len(gps_fixes)}/{len(frame_paths)} frames have real GPS fixes")
    elif gps_log_path and Path(gps_log_path).exists():
        from geo.flight_metadata import parse_flight_log
        gps_fixes = parse_flight_log(gps_log_path)
        telemetry_provenance = "REAL"
    elif allow_simulated_gps:
        print("  [Notice] No real telemetry supplied — using SIMULATED GPS fixes "
              "anchored at default flight origin (explicitly requested via allow_simulated_gps).")
        origin_lat, origin_lon, origin_alt = default_origin
        for pose in poses:
            name = Path(pose.frame_path).name
            cam_center = -pose.rotation.T @ pose.translation
            lat, lon, alt = enu_to_gps(cam_center[None, :], origin_lat, origin_lon, origin_alt)[0]
            gps_fixes.append(GpsFix(name, lat, lon, alt))
        telemetry_provenance = "SIMULATED"

    has_geo = len(gps_fixes) >= 3
    if has_geo:
        align_result = align_geometry_to_gps(clean_geom, gps_fixes)
        print(f"  Alignment: Scale factor = {align_result.scale_factor:.4f}")
        print(f"  Mean GPS residual = {align_result.mean_alignment_residual_m:.3f} m")
    else:
        # Phase A provenance rule: no real/opted-in GPS -> LOCAL_METRIC mode. Points
        # stay in COLMAP's own arbitrary-scale frame; no coordinate is invented.
        print("  [LOCAL_METRIC MODE] No real GPS available (and allow_simulated_gps=False) — "
              "georeferencing skipped. Output points remain in an arbitrary, ungeoreferenced "
              "SfM-scale frame. Pass --telemetry, --gps-log, or --allow-simulated-gps to georeference.")
        from types import SimpleNamespace
        align_result = SimpleNamespace(
            points_enu=clean_points,
            aligned_poses=poses,
            scale_factor=None,
            origin_lat=None,
            origin_lon=None,
            origin_alt_m=None,
            n_gps_correspondences=0,
            mean_alignment_residual_m=None,
        )

    # ---------------------------------------------------------
    # Stage 5.5 [optional] — Phase C: Geo-Constrained Pose Refinement
    # ---------------------------------------------------------
    geo_ba_report: dict | None = None
    if has_geo and run_geo_constrained_ba:
        print("\n[Stage 5.5] Geo-constrained pose refinement (diagnostic trajectory)...")
        point_id_to_aligned_xyz = dict(zip(clean_point_ids, align_result.points_enu))
        sparse_image_by_name = {Path(img["name"]).name: img for img in sparse_model["images"].values()}

        camera_names, rotations, intrinsics_list, observations = [], [], [], []
        for pose in align_result.aligned_poses:
            name = Path(pose.frame_path).name
            src_img = sparse_image_by_name.get(name)
            obs = []
            if src_img is not None:
                for px, py, pid in src_img["points2d"]:
                    xyz = point_id_to_aligned_xyz.get(pid)
                    if xyz is not None:
                        obs.append((px, py, xyz))
            camera_names.append(name)
            rotations.append(pose.rotation)
            intrinsics_list.append(pose.intrinsics)
            observations.append(obs)

        gps_priors_enu = {}
        for gf in gps_fixes:
            if gf.frame_name in camera_names:
                e, n, u = lla_to_enu(gf.lat, gf.lon, gf.alt_m, align_result.origin_lat, align_result.origin_lon, align_result.origin_alt_m)
                gps_priors_enu[gf.frame_name] = np.array([e, n, u])

        ba_result = refine_poses_with_gps_priors(
            camera_names=camera_names,
            rotations=rotations,
            intrinsics=intrinsics_list,
            initial_centers=list(align_result.camera_centers_enu),
            observations=observations,
            gps_priors_enu=gps_priors_enu,
            gps_weight=geo_ba_gps_weight,
        )
        print(f"  Refined {ba_result.n_cameras_refined} camera positions over {ba_result.n_observations} observations")
        print(f"  Mean reprojection error: {ba_result.mean_reprojection_error_px:.3f} px, "
              f"mean GPS residual: {ba_result.mean_gps_residual_m:.3f} m")
        geo_ba_report = {
            "n_cameras_refined": ba_result.n_cameras_refined,
            "n_observations": ba_result.n_observations,
            "mean_reprojection_error_px": ba_result.mean_reprojection_error_px,
            "mean_gps_residual_m": ba_result.mean_gps_residual_m,
            "gps_weight_used": geo_ba_gps_weight,
        }
        refined_trajectory = {
            name: {"enu": ba_result.refined_centers[name].tolist()} for name in camera_names
        }
        (deliverables_dir / "refined_trajectory.json").write_text(json.dumps({
            "note": "Diagnostic pose-only geo-constrained refinement (Phase C). Does NOT "
                    "replace the primary georeferenced point cloud/mesh — camera positions only.",
            "summary": geo_ba_report,
            "trajectory": refined_trajectory,
        }, indent=2))
        print(f"  [Deliverable] Geo-constrained trajectory: {deliverables_dir / 'refined_trajectory.json'}")

    # ---------------------------------------------------------
    # Stage 6: Semantic Class Tagging & Confidence
    # ---------------------------------------------------------
    print("\n[Stage 6/7] Applying semantic class tags & confidence tiers...")
    class_tags = tag_points_by_class(clean_points, clean_point_ids, sparse_model, masks_dir or "")
    class_names = tags_to_class_names(class_tags)
    conf_tiers = compute_confidence_tiers(clean_track_len, clean_reproj_err)
    tier_names = np.array(["low", "medium", "high"])[conf_tiers]

    # ---------------------------------------------------------
    # Stage 7: Deliverables Generation
    # ---------------------------------------------------------
    print("\n[Stage 7/7] Generating GIS & 3D Deliverables...")

    # 1. Point Clouds: .las and .laz
    epsg_code = utm_epsg_for_lonlat(align_result.origin_lon, align_result.origin_lat) if has_geo else None
    las_path = deliverables_dir / "classified_pointcloud.las"
    laz_path = deliverables_dir / "classified_pointcloud.laz"
    export_point_cloud_to_las(
        points_xyz=align_result.points_enu,
        output_path=las_path,
        points_rgb=clean_rgb,
        points_class=class_tags,
        points_confidence=clean_track_len,
        crs=epsg_code,
    )
    export_point_cloud_to_las(
        points_xyz=align_result.points_enu,
        output_path=laz_path,
        points_rgb=clean_rgb,
        points_class=class_tags,
        points_confidence=clean_track_len,
        crs=epsg_code,
    )
    print(f"  [Deliverable] ASPRS LAS: {las_path} ({las_path.stat().st_size / 1024:.1f} KB)")
    print(f"  [Deliverable] ASPRS LAZ: {laz_path} ({laz_path.stat().st_size / 1024:.1f} KB)")

    # 2. Elevation Rasters (DSM / DTM) — meaningless in an ungeoreferenced local frame
    dsm_dtm_stats: dict = {}
    if has_geo:
        dsm_path = deliverables_dir / "dsm.tif"
        dtm_path = deliverables_dir / "dtm.tif"
        dsm_dtm_stats = export_dsm_dtm(
            points_enu=align_result.points_enu,
            class_names=class_names,
            origin_lat=align_result.origin_lat,
            origin_lon=align_result.origin_lon,
            dsm_out_path=str(dsm_path),
            dtm_out_path=str(dtm_path),
            cell_size_m=0.5,
        )
        print(f"  [Deliverable] DSM GeoTIFF: {dsm_path} (Grid: {dsm_dtm_stats['dsm_shape']})")
        print(f"  [Deliverable] DTM GeoTIFF: {dtm_path}")

        # 3. Orthomosaic
        z_ref = estimate_ground_z_ref(align_result.points_enu, class_names)
        x_min, y_min = align_result.points_enu[:, :2].min(axis=0)
        x_max, y_max = align_result.points_enu[:, :2].max(axis=0)
        ortho_img, ortho_cnt = build_orthomosaic(
            poses=align_result.aligned_poses,
            image_dir=image_folder,
            x_min=float(x_min),
            x_max=float(x_max),
            y_min=float(y_min),
            y_max=float(y_max),
            z_ref=z_ref,
            gsd_m=0.2,
        )
        ortho_path = deliverables_dir / "orthomosaic.png"
        cv2.imwrite(str(ortho_path), ortho_img)
        print(f"  [Deliverable] Orthomosaic: {ortho_path} (Size: {ortho_img.shape[1]}x{ortho_img.shape[0]})")
    else:
        print("  [LOCAL_METRIC MODE] Skipping DSM/DTM/orthomosaic — these require a real "
              "georeferenced, metrically-scaled point cloud, which is not available.")

    # 4. Metric Quality Report
    from dataclasses import asdict
    report_path = deliverables_dir / "confidence_report.json"
    breakdowns = per_class_confidence_breakdown(conf_tiers, clean_track_len, clean_reproj_err, class_names)
    class_breakdown = [asdict(b) for b in breakdowns]
    report_data = {
        "dataset": str(input_path),
        "telemetry_provenance": telemetry_provenance,
        "georeferenced": has_geo,
        "total_input_frames": len(frame_paths),
        "registered_frames": n_reg_images,
        "registration_rate_pct": float(n_reg_images / len(frame_paths) * 100),
        "sparse_points": clean_points.shape[0],
        "scale_factor": float(align_result.scale_factor) if has_geo else None,
        "mean_gps_residual_m": float(align_result.mean_alignment_residual_m) if has_geo else None,
        "mean_reprojection_error_px": float(clean_reproj_err.mean()) if len(clean_reproj_err) else None,
        "high_confidence_points_pct": float((conf_tiers == 2).mean() * 100),
        "class_breakdown": class_breakdown,
        "volumetric_metrics": dsm_dtm_stats.get("volumetric", {}),
        "georeference_origin": {
            "lat": align_result.origin_lat,
            "lon": align_result.origin_lon,
            "alt_m": align_result.origin_alt_m,
            "epsg": epsg_code,
        } if has_geo else None,
        "geo_constrained_ba": geo_ba_report,
    }
    report_path.write_text(json.dumps(report_data, indent=2))
    print(f"  [Deliverable] Metric Report: {report_path}")

    # 5. CesiumJS Web Viewer Bundle — needs real lat/lon, so only in georeferenced mode
    if has_geo:
        wgs84_coords = enu_to_gps(
            align_result.points_enu,
            align_result.origin_lat,
            align_result.origin_lon,
            align_result.origin_alt_m,
        )
        viewer_points = []
        for i in range(wgs84_coords.shape[0]):
            viewer_points.append({
                "lat": float(wgs84_coords[i, 0]),
                "lon": float(wgs84_coords[i, 1]),
                "alt": float(wgs84_coords[i, 2]),
                "class": class_names[i],
                "confidence": tier_names[i],
            })
        origin_dict = {"lat": align_result.origin_lat, "lon": align_result.origin_lon, "alt": align_result.origin_alt_m}
        (viewer_dir / "points.json").write_text(json.dumps({
            "origin": origin_dict,
            "origin_lla": origin_dict,
            "n_points": len(viewer_points),
            "classes": sorted(set(class_names)),
            "points": viewer_points,
        }))
        print(f"  [Viewer] Prepared CesiumJS point bundle: {viewer_dir / 'points.json'}")

        # Real per-frame flight trajectory (registered cameras only) — replaces any
        # synthetic/fabricated path the viewer might otherwise need to invent.
        traj_wgs84 = enu_to_gps(
            align_result.camera_centers_enu,
            align_result.origin_lat, align_result.origin_lon, align_result.origin_alt_m,
        )
        trajectory_points = [
            {"frame": Path(pose.frame_path).name, "lat": float(traj_wgs84[i, 0]),
             "lon": float(traj_wgs84[i, 1]), "alt": float(traj_wgs84[i, 2])}
            for i, pose in enumerate(align_result.aligned_poses)
        ]
        (viewer_dir / "trajectory.json").write_text(json.dumps({
            "origin": origin_dict, "n_frames": len(trajectory_points), "trajectory": trajectory_points,
        }))
        print(f"  [Viewer] Prepared real flight trajectory: {viewer_dir / 'trajectory.json'} "
              f"({len(trajectory_points)} frames)")
    else:
        print("  [LOCAL_METRIC MODE] Skipping CesiumJS viewer bundle (requires real lat/lon).")

    # 6. Scaled 3D Mesh Export (scale factor applied only when georeferenced; otherwise
    # the mesh stays in COLMAP's own arbitrary units, clearly not real-world meters)
    mesh_scale = float(align_result.scale_factor) if has_geo else 1.0
    dense_mesh_path = reconstruction_dir / "dense" / "meshed-poisson.ply"
    mesh = None
    try:
        import open3d as o3d
        if dense_mesh_path.exists():
            mesh = o3d.io.read_triangle_mesh(str(dense_mesh_path))
        elif len(clean_points) >= 10:
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(clean_points)
            if len(clean_rgb) == len(clean_points):
                pcd.colors = o3d.utility.Vector3dVector(clean_rgb.astype(np.float64) / 255.0)
            pcd.estimate_normals()
            mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=8)

        if mesh is not None and len(mesh.vertices) > 0:
            verts = np.asarray(mesh.vertices) * mesh_scale
            mesh.vertices = o3d.utility.Vector3dVector(verts)
            mesh.compute_vertex_normals()
            glb_out = viewer_dir / "mesh_scaled.glb"
            o3d.io.write_triangle_mesh(str(glb_out), mesh)
            shutil.copy(str(glb_out), deliverables_dir / "mesh_textured.glb")
            ply_out = deliverables_dir / "mesh_textured.ply"
            o3d.io.write_triangle_mesh(str(ply_out), mesh)
            print(f"  [Deliverable] Scaled 3D Mesh: {deliverables_dir / 'mesh_textured.glb'}")

            # 6b. [optional] Phase F: real multi-view UV texture bake, as a
            # separate file — the vertex-colored export above is already the
            # tested default; this is an additive, opt-in upgrade.
            if run_uv_texture_mapping:
                try:
                    faces = np.asarray(mesh.triangles, dtype=np.int32)
                    img_candidates = [p for p in image_folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
                    if img_candidates:
                        sample_img = cv2.imread(str(img_candidates[0]))
                        img_h, img_w = sample_img.shape[:2]
                        cam_views = []
                        for i, pose in enumerate(poses):
                            img_path = image_folder / Path(pose.frame_path).name
                            if not img_path.exists():
                                continue
                            cam_views.append(CameraView(
                                camera_idx=i,
                                image_path=img_path,
                                rotation=pose.rotation,
                                translation=pose.translation * mesh_scale,
                                intrinsics=pose.intrinsics,
                                width=img_w,
                                height=img_h,
                            ))
                        uv_glb_out = deliverables_dir / "mesh_uv_textured.glb"
                        UVTextureMapper.bake_and_export_glb(verts, faces, cam_views, uv_glb_out)
                        print(f"  [Deliverable] UV-textured 3D Mesh: {uv_glb_out}")
                except Exception as e:
                    print(f"  [Notice] UV texture mapping skipped ({e})")
    except Exception as e:
        print(f"  [Notice] Mesh conversion skipped ({e})")

    print("\n========================================================")
    print("  Pipeline Completed Successfully!")
    print(f"  All deliverables written to: {deliverables_dir.resolve()}")
    print("========================================================\n")

    return report_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SIH26158 Single-Pass Drone 3D Reconstruction Pipeline")
    parser.add_argument("--input", required=True, help="Input video file or directory of image frames")
    parser.add_argument("--output-dir", default="outputs/pipeline_run", help="Target output directory")
    parser.add_argument("--gps-log", default=None, help="Legacy path to a raw GPS log file")
    parser.add_argument("--telemetry", default=None, help="Path to a FlightSession telemetry JSON (preferred)")
    parser.add_argument("--allow-simulated-gps", action="store_true",
                         help="Explicitly allow fabricated GPS when no real telemetry is given "
                              "(default: LOCAL_METRIC mode, no invented coordinates)")
    parser.add_argument("--adaptive-keyframes", action="store_true",
                         help="Use multi-criteria adaptive keyframe selection instead of fixed-interval extraction")
    parser.add_argument("--geo-constrained-ba", action="store_true",
                         help="Run Phase C diagnostic geo-constrained pose refinement after alignment")
    parser.add_argument("--geo-ba-gps-weight", type=float, default=1.0,
                         help="How strongly geo-constrained BA trusts GPS over reprojection (see docstring)")
    parser.add_argument("--uv-texture-mapping", action="store_true",
                         help="Bake a real multi-view UV-textured GLB (Phase F) alongside the default vertex-colored mesh")
    parser.add_argument("--dense", action="store_true", help="Run dense Poisson meshing")
    parser.add_argument("--reuse-sparse", default=None, help="Reuse existing sparse reconstruction (path or flag)")
    args = parser.parse_args()

    run_pipeline(
        input_path=args.input,
        output_dir=args.output_dir,
        gps_log_path=args.gps_log,
        telemetry_path=args.telemetry,
        allow_simulated_gps=args.allow_simulated_gps,
        run_dense=args.dense,
        reuse_sparse=args.reuse_sparse or False,
        use_adaptive_keyframes=args.adaptive_keyframes,
        run_geo_constrained_ba=args.geo_constrained_ba,
        geo_ba_gps_weight=args.geo_ba_gps_weight,
        run_uv_texture_mapping=args.uv_texture_mapping,
    )
