"use client";

import React from "react";
import {
  Activity,
  Compass,
  Download,
  Eye,
  Layers,
  MapPin,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
} from "lucide-react";
import { MissionSummary, MissionDetail } from "@/types/mission";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const fmt = (v: number | null | undefined, digits = 1, suffix = "") =>
  v === null || v === undefined ? "—" : `${v.toFixed(digits)}${suffix}`;

interface MissionSidebarProps {
  mission?: MissionSummary;
  detail?: MissionDetail | null;
  pointCloudVisible: boolean;
  onTogglePointCloud: () => void;
  trajectoryVisible: boolean;
  onToggleTrajectory: () => void;
  colorMode: "semantic" | "uncertainty";
  onChangeColorMode: (mode: "semantic" | "uncertainty") => void;
  confidenceThreshold: number;
  onChangeConfidenceThreshold: (val: number) => void;
}

export const MissionSidebar: React.FC<MissionSidebarProps> = ({
  mission,
  detail,
  pointCloudVisible,
  onTogglePointCloud,
  trajectoryVisible,
  onToggleTrajectory,
  colorMode,
  onChangeColorMode,
  confidenceThreshold,
  onChangeConfidenceThreshold,
}) => {
  const rep = detail?.report;
  const sq = mission?.sensor_quality || rep?.sensor_quality;
  const semq = mission?.semantic_quality || rep?.semantic_quality;

  const deliverables = [
    { name: "classified_pointcloud.las", label: "ASPRS LAS Point Cloud", ext: "LAS" },
    { name: "classified_pointcloud.laz", label: "ASPRS Compressed LAZ", ext: "LAZ" },
    { name: "dsm.tif", label: "Digital Surface Model", ext: "GeoTIFF" },
    { name: "dtm.tif", label: "Digital Terrain Model", ext: "GeoTIFF" },
    { name: "orthomosaic.png", label: "Nadir Orthomosaic", ext: "PNG" },
    { name: "mesh_textured.glb", label: "Georeferenced 3D Mesh", ext: "GLB" },
    { name: "confidence_report.json", label: "Scientific Metric Report", ext: "JSON" },
  ];

  return (
    <aside className="w-80 border-r border-zinc-800 bg-zinc-950 flex flex-col h-full overflow-y-auto shrink-0 select-none text-xs">
      {/* 1. Mission Key Metrics */}
      <div className="p-4 border-b border-zinc-800 space-y-3">
        <div className="flex items-center justify-between text-zinc-400 font-medium">
          <span className="flex items-center gap-1.5 uppercase tracking-wider text-[10px] text-zinc-500 font-mono">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            Flight Metrics
          </span>
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">
            {mission?.status ?? "NO MISSION"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="bg-zinc-900/90 p-2 rounded border border-zinc-800">
            <div className="text-[10px] text-zinc-500">Registered Frames</div>
            <div className="text-sm font-bold text-zinc-200 mt-0.5">
              {mission?.registered_frames ?? "—"} / {mission?.total_frames ?? "—"}
            </div>
            <div className="text-[10px] text-emerald-400 font-mono">
              {fmt(mission?.registration_rate_pct, 1, "% rate")}
            </div>
          </div>

          <div className="bg-zinc-900/90 p-2 rounded border border-zinc-800">
            <div className="text-[10px] text-zinc-500">Sparse Triangulation</div>
            <div className="text-sm font-bold text-zinc-200 mt-0.5">
              {mission?.sparse_points != null ? `${mission.sparse_points.toLocaleString()} pts` : "—"}
            </div>
            <div className="text-[10px] text-zinc-400 font-mono">
              Err: {fmt(rep?.mean_reprojection_error_px, 2, " px")}
            </div>
          </div>
        </div>

        {/* Sensor Fusion Card */}
        {sq && (
          <div className="bg-zinc-900/90 p-2.5 rounded border border-amber-900/40 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-amber-300 flex items-center gap-1">
                <Compass className="w-3.5 h-3.5 text-amber-400" />
                Sensor-Fusion Engine
              </span>
              <span className="text-[10px] font-mono text-amber-400 bg-amber-950/80 px-1.5 py-0.5 rounded">
                BNR: {sq.baseline_to_noise_ratio.toFixed(2)}
              </span>
            </div>
            <p className="text-[10px] text-zinc-400 leading-relaxed">
              {sq.summary}
            </p>
            <div className="grid grid-cols-2 gap-1 text-[10px] text-zinc-500 pt-1 border-t border-zinc-800">
              <div>Baseline: <span className="text-zinc-300 font-mono">{sq.trajectory_baseline_m.toFixed(1)}m</span></div>
              <div>Noise: <span className="text-zinc-300 font-mono">~{sq.estimated_noise_m.toFixed(1)}m</span></div>
            </div>
          </div>
        )}

        {/* Semantic Quality Card — independent from GPS/sensor quality above.
            High multi-view agreement does not imply correct class labels: the
            segmentation model can be confidently wrong in the same way across
            every camera. This flags that failure mode via geometric plausibility
            of the class-tagged instances, not just voting agreement. */}
        {semq && semq.quality_tier !== "TRUSTED" && (
          <div className="bg-zinc-900/90 p-2.5 rounded border border-red-900/40 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-red-300 flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                Semantic Quality
              </span>
              <span className="text-[10px] font-mono text-red-400 bg-red-950/80 px-1.5 py-0.5 rounded">
                {semq.quality_tier.replace("_", " ")}
              </span>
            </div>
            <p className="text-[10px] text-zinc-400 leading-relaxed">
              {semq.summary}
            </p>
            {semq.mean_semantic_confidence != null && (
              <div className="grid grid-cols-2 gap-1 text-[10px] text-zinc-500 pt-1 border-t border-zinc-800">
                <div>Agreement: <span className="text-zinc-300 font-mono">{(semq.mean_semantic_confidence * 100).toFixed(0)}%</span></div>
                <div>Oversized: <span className="text-zinc-300 font-mono">{semq.oversized_instance_count}</span></div>
              </div>
            )}
          </div>
        )}
        {semq && semq.quality_tier === "TRUSTED" && (
          <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 px-1">
            <ShieldCheck className="w-3.5 h-3.5" />
            Semantic tags trusted (agreement {((semq.mean_semantic_confidence ?? 0) * 100).toFixed(0)}%, no oversized instances)
          </div>
        )}
      </div>

      {/* 2. GIS Layers & Visual Modes */}
      <div className="p-4 border-b border-zinc-800 space-y-3">
        <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono flex items-center gap-1.5 font-medium">
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          Layer Visualization
        </div>

        {/* Toggles */}
        <div className="space-y-2">
          <label className="flex items-center justify-between p-2 rounded bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700 cursor-pointer transition-colors">
            <span className="flex items-center gap-2 text-zinc-300">
              <Eye className="w-3.5 h-3.5 text-zinc-400" />
              3D Point Cloud
            </span>
            <input
              type="checkbox"
              checked={pointCloudVisible}
              onChange={onTogglePointCloud}
              className="accent-emerald-500 rounded"
            />
          </label>

          <label className="flex items-center justify-between p-2 rounded bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700 cursor-pointer transition-colors">
            <span className="flex items-center gap-2 text-zinc-300">
              <MapPin className="w-3.5 h-3.5 text-zinc-400" />
              Flight Trajectory
            </span>
            <input
              type="checkbox"
              checked={trajectoryVisible}
              onChange={onToggleTrajectory}
              className="accent-emerald-500 rounded"
            />
          </label>
        </div>

        {/* Color Mode Switcher */}
        <div className="space-y-1.5 pt-1">
          <div className="text-[10px] text-zinc-400 font-medium">Color Palette:</div>
          <div className="grid grid-cols-2 gap-1.5 bg-zinc-900 p-1 rounded border border-zinc-800">
            <button
              onClick={() => onChangeColorMode("semantic")}
              className={`py-1 px-2 rounded text-[11px] font-medium transition-all ${
                colorMode === "semantic"
                  ? "bg-emerald-600 text-white shadow"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              UAVid Classes
            </button>
            <button
              onClick={() => onChangeColorMode("uncertainty")}
              className={`py-1 px-2 rounded text-[11px] font-medium transition-all ${
                colorMode === "uncertainty"
                  ? "bg-amber-600 text-white shadow"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Uncertainty Heatmap
            </button>
          </div>
        </div>

        {/* Confidence Filter Slider */}
        <div className="space-y-1 pt-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-zinc-400 flex items-center gap-1">
              <Sliders className="w-3 h-3" />
              Confidence Cutoff:
            </span>
            <span className="font-mono text-zinc-200">
              {(confidenceThreshold * 100).toFixed(0)}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={confidenceThreshold}
            onChange={(e) => onChangeConfidenceThreshold(parseFloat(e.target.value))}
            aria-label="Confidence threshold"
            className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </div>
      </div>

      {/* 3. GIS Deliverables Inventory */}
      <div className="p-4 space-y-2 flex-1">
        <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono flex items-center gap-1.5 font-medium">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          GIS & 3D Deliverables
        </div>

        <div className="space-y-1.5">
          {deliverables.map((item) => (
            <div
              key={item.name}
              className="flex items-center justify-between p-2 rounded bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700 transition-colors group"
            >
              <div className="min-w-0 pr-2">
                <div className="text-zinc-200 font-medium truncate">{item.label}</div>
                <div className="text-[10px] text-zinc-500 font-mono">{item.ext}</div>
              </div>
              {mission?.id ? (
                <a
                  href={`${API_BASE}/static/outputs/${mission.id}/deliverables/${item.name}`}
                  download={item.name}
                  target="_blank"
                  rel="noreferrer"
                  className="p-1.5 rounded bg-zinc-800 group-hover:bg-emerald-600 text-zinc-400 group-hover:text-white transition-colors shrink-0"
                  title={`Download ${item.name}`}
                  aria-label={`Download ${item.name}`}
                >
                  <Download className="w-3.5 h-3.5" />
                </a>
              ) : (
                <span
                  className="p-1.5 rounded bg-zinc-900 text-zinc-700 shrink-0 cursor-not-allowed"
                  title="No mission selected"
                  aria-label="No mission selected"
                >
                  <Download className="w-3.5 h-3.5" />
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
};
