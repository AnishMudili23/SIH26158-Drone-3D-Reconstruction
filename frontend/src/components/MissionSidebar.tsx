"use client";

import React from "react";
import { MissionSummary, MissionDetail } from "@/types/mission";

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
  colorMode?: "semantic" | "uncertainty";
  onChangeColorMode?: (mode: "semantic" | "uncertainty") => void;
  confidenceThreshold?: number;
  onChangeConfidenceThreshold?: (val: number) => void;
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
}) => {
  const frames = mission?.total_frames || 350;
  const points = mission?.sparse_points || 32289;
  const pointsStr = points >= 1000 ? `${(points / 1000).toFixed(1)}K` : `${points}`;
  const structuresCount = mission?.building_count || 2;
  const missionType = mission?.mission_type || "Building Inspection";

  return (
    <aside className="w-56 border-r border-zinc-850 bg-[#06080d] flex flex-col h-full overflow-y-auto shrink-0 select-none text-xs">
      <div className="p-4 space-y-6">
        {/* OVERVIEW SECTION */}
        <div className="space-y-3">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider font-mono">
            MISSION
          </div>

          <div>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Ready
            </span>
          </div>

          <div className="text-zinc-200 font-medium text-xs">
            {missionType}
          </div>

          <div className="space-y-1 text-zinc-400 font-mono text-xs">
            <div>{frames} frames</div>
            <div>{pointsStr} points</div>
            <div>{structuresCount} structures</div>
          </div>
        </div>

        {/* LAYERS SECTION */}
        <div className="space-y-3 pt-4 border-t border-zinc-800/80">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider font-mono">
            LAYERS
          </div>

          <div className="space-y-2.5">
            <label className="flex items-center gap-2.5 text-zinc-200 cursor-pointer hover:text-white transition-colors">
              <input
                type="checkbox"
                checked={pointCloudVisible}
                onChange={onTogglePointCloud}
                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
              />
              <span>3D Scene</span>
            </label>

            <label className="flex items-center gap-2.5 text-zinc-200 cursor-pointer hover:text-white transition-colors">
              <input
                type="checkbox"
                checked={trajectoryVisible}
                onChange={onToggleTrajectory}
                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
              />
              <span>Flight Path</span>
            </label>

            <label className="flex items-center gap-2.5 text-zinc-200 cursor-pointer hover:text-white transition-colors">
              <input
                type="checkbox"
                checked={structuresVisible}
                onChange={onToggleStructures}
                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
              />
              <span>Structures</span>
            </label>
          </div>

          <div className="h-px bg-zinc-850 my-2" />

          <div className="space-y-2.5">
            <label className="flex items-center gap-2.5 text-zinc-400 cursor-pointer hover:text-zinc-200 transition-colors">
              <input
                type="checkbox"
                checked={terrainVisible}
                onChange={onToggleTerrain}
                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
              />
              <span>Terrain</span>
            </label>

            <label className="flex items-center gap-2.5 text-zinc-400 cursor-pointer hover:text-zinc-200 transition-colors">
              <input
                type="checkbox"
                checked={damageVisible}
                onChange={onToggleDamage}
                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
              />
              <span>Damage</span>
            </label>

            <label className="flex items-center gap-2.5 text-zinc-400 cursor-pointer hover:text-zinc-200 transition-colors">
              <input
                type="checkbox"
                checked={uncertaintyVisible}
                onChange={onToggleUncertainty}
                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700 text-emerald-600 accent-emerald-500 cursor-pointer"
              />
              <span>Uncertainty</span>
            </label>
          </div>
        </div>
      </div>
    </aside>
  );
};
