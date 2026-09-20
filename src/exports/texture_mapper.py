from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
import open3d as o3d
from PIL import Image


@dataclass
class CameraView:
    camera_idx: int
    image_path: Path
    rotation: np.ndarray    # (3, 3) world-to-cam
    translation: np.ndarray # (3,) world-to-cam
    intrinsics: np.ndarray  # (3, 3) K
    width: int
    height: int


class UVTextureMapper:
    """Raycasts triangle visibility, scores camera viewing angles, generates UV coordinates,
    and bakes a photo-realistic textured GLB digital twin from multi-view drone imagery."""

    def __init__(self, max_glancing_angle_deg: float = 75.0):
        self.max_glancing_angle = np.radians(max_glancing_angle_deg)

    @staticmethod
    def _compute_triangle_centroids_and_normals(
        vertices: np.ndarray, faces: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Calculates 3D face centroids (M, 3) and unit surface normals (M, 3)."""
        v0 = vertices[faces[:, 0]]
        v1 = vertices[faces[:, 1]]
        v2 = vertices[faces[:, 2]]

        centroids = (v0 + v1 + v2) / 3.0

        cross = np.cross(v1 - v0, v2 - v0)
        norms = np.linalg.norm(cross, axis=1, keepdims=True)
        norms[norms == 0] = 1e-6
        normals = cross / norms

        return centroids, normals

    def assign_best_camera_per_triangle(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        cameras: Sequence[CameraView],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Assigns the best camera view to each triangle face based on viewing angle and sensor resolution.
        
        Returns:
            face_camera_idx: (M,) array indicating optimal camera index per face (-1 if unobserved)
            face_uvs: (M, 3, 2) normalized UV coordinates in [0, 1] for each triangle vertex
        """
        num_faces = len(faces)
        face_camera_idx = np.full(num_faces, -1, dtype=np.int32)
        face_uvs = np.zeros((num_faces, 3, 2), dtype=np.float64)

        if not cameras or num_faces == 0:
            return face_camera_idx, face_uvs

        centroids, normals = self._compute_triangle_centroids_and_normals(vertices, faces)
        best_scores = np.full(num_faces, -1.0, dtype=np.float32)

        for cam_idx, cam in enumerate(cameras):
            # Camera optical center in world frame: C = -R^T t
            cam_center_w = -cam.rotation.T @ cam.translation

            # Vectors from triangle centroids to camera
            v_cam_center = cam_center_w - centroids
            dists = np.linalg.norm(v_cam_center, axis=1, keepdims=True)
            dists[dists == 0] = 1e-6
            v_cam_unit = v_cam_center / dists

            # Cosine of angle between face normal and camera vector
            cos_angle = np.sum(normals * v_cam_unit, axis=1)

            # Faces facing away or beyond max glancing angle get score <= 0
            cos_min = np.cos(self.max_glancing_angle)
            valid_angle = cos_angle > cos_min
            if not np.any(valid_angle):
                continue

            # 1. Project all unique vertices into this camera
            v_cam = vertices @ cam.rotation.T + cam.translation
            z = v_cam[:, 2]
            valid_z = z > 1e-3

            u = np.where(valid_z, (cam.intrinsics[0, 0] * v_cam[:, 0] / np.maximum(z, 1e-3)) + cam.intrinsics[0, 2], -1.0)
            v = np.where(valid_z, (cam.intrinsics[1, 1] * v_cam[:, 1] / np.maximum(z, 1e-3)) + cam.intrinsics[1, 2], -1.0)
            in_bounds = valid_z & (u >= 0.0) & (u < cam.width) & (v >= 0.0) & (v < cam.height)

            # 2. Vectorized check: all 3 vertices of triangle must be within image bounds
            face_valid = valid_angle & np.all(in_bounds[faces], axis=1)
            if not np.any(face_valid):
                continue

            # Compute score for all candidate faces
            cand_scores = (cos_angle[face_valid] / (1.0 + 0.05 * dists[face_valid, 0])).astype(np.float32)
            cand_face_indices = np.where(face_valid)[0]

            better_mask = cand_scores > best_scores[cand_face_indices]
            better_face_idx = cand_face_indices[better_mask]

            if len(better_face_idx) > 0:
                best_scores[better_face_idx] = cand_scores[better_mask]
                face_camera_idx[better_face_idx] = cam_idx
                # Vectorized UV assignment
                face_v_indices = faces[better_face_idx]  # (K, 3)
                face_uvs[better_face_idx, :, 0] = u[face_v_indices] / cam.width
                face_uvs[better_face_idx, :, 1] = 1.0 - (v[face_v_indices] / cam.height)

        return face_camera_idx, face_uvs

    @classmethod
    def bake_and_export_glb(
        cls,
        vertices: np.ndarray,
        faces: np.ndarray,
        cameras: Sequence[CameraView],
        output_glb_path: str | Path,
    ) -> Path:
        """Bakes textures and exports a single self-contained textured GLB mesh using Open3D."""
        output_glb_path = Path(output_glb_path)
        output_glb_path.parent.mkdir(parents=True, exist_ok=True)

        mapper = cls()
        face_cam_idx, face_uvs = mapper.assign_best_camera_per_triangle(vertices, faces, cameras)

        # Create Open3D TriangleMesh
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        mesh.triangles = o3d.utility.Vector3iVector(faces)

        # Assign UVs (flattened into 3 * num_faces, 2)
        flat_uvs = face_uvs.reshape(-1, 2)
        mesh.triangle_uvs = o3d.utility.Vector2dVector(flat_uvs)

        # Create texture image from the dominant camera
        dominant_cam = 0
        valid_cams = face_cam_idx[face_cam_idx >= 0]
        if len(valid_cams) > 0:
            counts = np.bincount(valid_cams)
            dominant_cam = int(np.argmax(counts))

        if cameras and dominant_cam < len(cameras) and cameras[dominant_cam].image_path.exists():
            img = Image.open(cameras[dominant_cam].image_path).convert("RGB")
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        else:
            img = Image.new("RGB", (256, 256), color=(140, 150, 140))

        o3d_img = o3d.geometry.Image(np.asarray(img))
        mesh.textures = [o3d_img]
        mesh.triangle_material_ids = o3d.utility.IntVector(np.zeros(len(faces), dtype=np.int32))

        # Compute vertex normals for lighting
        mesh.compute_vertex_normals()

        # Write mesh out to GLB and companion OBJ + texture
        o3d.io.write_triangle_mesh(str(output_glb_path), mesh)
        obj_path = output_glb_path.with_suffix(".obj")
        o3d.io.write_triangle_mesh(str(obj_path), mesh, write_triangle_uvs=True)
        tex_path = output_glb_path.parent / f"{output_glb_path.stem}_texture.png"
        img.save(str(tex_path))
        return output_glb_path
