"use client";

import React from "react";
import {
  Download,
  Eye,
  Layers,
  MapPin,
  ShieldCheck,
  Sparkles,
  FileText,
  Compass,
  CheckCircle2,
  Box,
} from "lucide-react";
import { MissionSummary, MissionDetail } from "@/types/mission";
import { getAssetDownloadUrl } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface MissionSidebarProps {
  mission?: MissionSummary;
  detail?: MissionDetail | null;
  // Layers
  pointCloudVisible: boolean;
  onTogglePointCloud: () => void;
  trajectoryVisible: boolean;
  onToggleTrajectory: () => void;
  structuresVisible?: boolean;
  onToggleStructures?: () => void;
  terrainVisible?: boolean;
  onToggleTerrain?: () => void;
  damageVisible?: boolean;
  onToggleDamage?: () => void;
  uncertaintyVisible?: boolean;
  onToggleUncertainty?: () => void;
  colorMode: "semantic" | "uncertainty";
  onChangeColorMode: (mode: "semantic" | "uncertainty") => void;
  confidenceThreshold: number;
  onChangeConfidenceThreshold: (val: number) => void;
  onOpenExport3D?: () => void;
  onFocus3DModel?: () => void;
}

export const MissionSidebar: React.FC<MissionSidebarProps> = ({
  mission,
  detail,
  pointCloudVisible,
  onTogglePointCloud,
  trajectoryVisible,
  onToggleTrajectory,
  structuresVisible = true,
  onToggleStructures,
  terrainVisible = false,
  onToggleTerrain,
  damageVisible = false,
  onToggleDamage,
  uncertaintyVisible = false,
  onToggleUncertainty,
  onOpenExport3D,
  onFocus3DModel,
}) => {
  const sq = mission?.sensor_quality || detail?.report?.sensor_quality;
  const isHighQuality = sq?.quality_tier === "STRONG_GPS";
  const missionId = mission?.id || "zurich_mav_mission";
  const isDemo = mission?.is_demo || missionId === "zurich_mav_mission";

  const deliverables = [
    {
      id: "3d_model",
      label: "3D Mesh Model",
      type: "GLB / PLY",
      isModel: true,
    },
    {
      id: "point_cloud",
      label: "Point Cloud",
      type: "LAS (Classified)",
      downloadAsset: "las",
    },
    {
      id: "orthomosaic",
      label: "Orthomosaic",
      type: "PNG (Geotagged)",
      downloadAsset: "ortho",
    },
    {
      id: "dsm",
      label: "DSM (Elevation)",
      type: "GeoTIFF",
      downloadAsset: "dsm",
    },
    {
      id: "dtm",
      label: "DTM (Bare Earth)",
      type: "GeoTIFF",
      downloadAsset: "dtm",
    },
    {
      id: "gis_package",
      label: "Full GIS Package",
      type: "ZIP",
      downloadAsset: "package",
    },
    {
      id: "mission_report",
      label: "Mission Audit Report",
      type: "HTML / PDF",
      isReport: true,
    },
  ];

  const handleDownload = (assetType: string) => {
    const url = getAssetDownloadUrl(missionId, assetType);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${missionId}_${assetType}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <aside className="w-80 border-r border-zinc-800 bg-[#07090e] flex flex-col h-full overflow-y-auto shrink-0 select-none text-xs">
      <div className="p-4 space-y-6">
        {/* 1. Main Mission Health & Key Indicators */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
              Mission Status
            </span>
            <div className="flex items-center gap-1.5">
              {isDemo && (
                <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-zinc-800 text-zinc-400 border border-zinc-750">
                  DEMO DATA
                </span>
              )}
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-700/60 shadow-sm shadow-emerald-900/40">
                <ShieldCheck className="w-3.5 h-3.5" />
                ● READY
              </span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="bg-zinc-900/80 border border-zinc-800 p-2.5 rounded-xl text-center">
              <div className="text-[10px] text-zinc-500 uppercase tracking-tight font-medium">Scene</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">12,428 m²</div>
            </div>

            <div className="bg-zinc-900/80 border border-zinc-800 p-2.5 rounded-xl text-center">
              <div className="text-[10px] text-zinc-500 uppercase tracking-tight font-medium">3D Points</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">32.2K</div>
            </div>

            <div className="bg-zinc-900/80 border border-zinc-800 p-2.5 rounded-xl text-center">
              <div className="text-[10px] text-zinc-500 uppercase tracking-tight font-medium">Sensors</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
                {isHighQuality ? "RTK GPS" : "GPS/IMU"}
              </div>
            </div>
          </div>
        </div>

        {/* 2. Simple Layer Switcher */}
        <div className="space-y-2.5 border-t border-zinc-800/80 pt-4">
          <div className="flex items-center justify-between text-zinc-300 font-bold uppercase tracking-wider text-[11px]">
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              Layers
            </span>
            <span className="text-[10px] text-zinc-500 font-normal">Toggle views</span>
          </div>

          <div className="space-y-1.5 bg-zinc-900/50 border border-zinc-800/80 rounded-xl p-2.5">
            {/* Layer 1: 3D Scene */}
            <label className="flex items-center justify-between p-1.5 hover:bg-zinc-800/50 rounded-lg cursor-pointer transition-colors">
              <span className="flex items-center gap-2 text-zinc-200 font-medium">
                <input
                  type="checkbox"
                  checked={pointCloudVisible}
                  onChange={onTogglePointCloud}
                  className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
                />
                3D Scene
              </span>
              <span className="text-[10px] font-mono text-zinc-500">Mesh & Points</span>
            </label>

            {/* Layer 2: Flight Path */}
            <label className="flex items-center justify-between p-1.5 hover:bg-zinc-800/50 rounded-lg cursor-pointer transition-colors">
              <span className="flex items-center gap-2 text-zinc-200 font-medium">
                <input
                  type="checkbox"
                  checked={trajectoryVisible}
                  onChange={onToggleTrajectory}
                  className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
                />
                Flight Path
              </span>
              <span className="text-[10px] font-mono text-zinc-500">GPS Track</span>
            </label>

            {/* Layer 3: Structures */}
            <label className="flex items-center justify-between p-1.5 hover:bg-zinc-800/50 rounded-lg cursor-pointer transition-colors">
              <span className="flex items-center gap-2 text-zinc-200 font-medium">
                <input
                  type="checkbox"
                  checked={structuresVisible}
                  onChange={onToggleStructures}
                  className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
                />
                Structures
              </span>
              <span className="text-[10px] font-mono text-zinc-500">3 Identified</span>
            </label>

            {/* Layer 4: Terrain */}
            <label className="flex items-center justify-between p-1.5 hover:bg-zinc-800/50 rounded-lg cursor-pointer transition-colors">
              <span className="flex items-center gap-2 text-zinc-300 font-medium">
                <input
                  type="checkbox"
                  checked={terrainVisible}
                  onChange={onToggleTerrain}
                  className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
                />
                Terrain
              </span>
              <span className="text-[10px] font-mono text-zinc-500">Elevation</span>
            </label>

            {/* Layer 5: Damage / Inspection */}
            <label className="flex items-center justify-between p-1.5 hover:bg-zinc-800/50 rounded-lg cursor-pointer transition-colors">
              <span className="flex items-center gap-2 text-zinc-300 font-medium">
                <input
                  type="checkbox"
                  checked={damageVisible}
                  onChange={onToggleDamage}
                  className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
                />
                Damage / Inspection
              </span>
              <span className="text-[10px] font-mono text-zinc-500">Health</span>
            </label>

            {/* Layer 6: Uncertainty */}
            <label className="flex items-center justify-between p-1.5 hover:bg-zinc-800/50 rounded-lg cursor-pointer transition-colors">
              <span className="flex items-center gap-2 text-zinc-300 font-medium">
                <input
                  type="checkbox"
                  checked={uncertaintyVisible}
                  onChange={onToggleUncertainty}
                  className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
                />
                Uncertainty
              </span>
              <span className="text-[10px] font-mono text-zinc-500">Heatmap</span>
            </label>
          </div>
        </div>

        {/* 3. Deliverables: Real Working Download / View Actions */}
        <div className="space-y-3 border-t border-zinc-800/80 pt-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              Use this mission
            </h3>
            <span className="text-[10px] font-mono text-zinc-500">Ready</span>
          </div>

          <div className="space-y-1.5 bg-zinc-900/60 border border-zinc-800/80 rounded-xl p-2">
            {deliverables.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-800/60 transition-colors group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-zinc-200 font-medium text-xs group-hover:text-emerald-300 transition-colors truncate">
                    {item.label}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  {item.isModel ? (
                    <>
                      <button
                        type="button"
                        onClick={onFocus3DModel}
                        className="px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-[11px] font-medium flex items-center gap-1 transition-colors cursor-pointer"
                        title="Focus 3D Viewport on Model"
                      >
                        <Eye className="w-3 h-3" />
                        <span>View</span>
                      </button>
                      <button
                        type="button"
                        onClick={onOpenExport3D}
                        className="px-2 py-1 rounded bg-zinc-800 hover:bg-emerald-600 text-zinc-300 hover:text-white text-[11px] font-medium flex items-center gap-1 transition-colors cursor-pointer"
                        title="Configure and Export 3D Model"
                      >
                        <Download className="w-3 h-3" />
                        <span>Download</span>
                      </button>
                    </>
                  ) : item.isReport ? (
                    <a
                      href={`${API_BASE}/api/missions/${missionId}/report`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2 py-1 rounded bg-zinc-800 hover:bg-emerald-600 text-zinc-300 hover:text-white text-[11px] font-medium flex items-center gap-1 transition-colors cursor-pointer"
                      title="Open printable mission audit report"
                    >
                      <FileText className="w-3 h-3" />
                      <span>Export</span>
                    </a>
                  ) : (
                    <button
                      type="button"
                      onClick={() => item.downloadAsset && handleDownload(item.downloadAsset)}
                      className="px-2 py-1 rounded bg-zinc-800 hover:bg-emerald-600 text-zinc-300 hover:text-white text-[11px] font-medium flex items-center gap-1 transition-colors cursor-pointer"
                      title={`Download ${item.type}`}
                    >
                      <Download className="w-3 h-3" />
                      <span>Export</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. Small "Powered by" Footer */}
      <div className="mt-auto border-t border-zinc-900 p-3 bg-[#05070a] text-center">
        <div className="text-[10px] text-zinc-500 font-medium uppercase tracking-wider mb-1">
          Powered by
        </div>
        <div className="text-[10px] font-mono text-zinc-400 flex flex-wrap items-center justify-center gap-x-1.5 gap-y-0.5">
          <span>COLMAP</span>
          <span>·</span>
          <span>Depth Anything V2</span>
          <span>·</span>
          <span>Cesium</span>
          <span>·</span>
          <span>GPS / IMU</span>
          <span>·</span>
          <span>GIS</span>
        </div>
      </div>
    </aside>
  );
};
