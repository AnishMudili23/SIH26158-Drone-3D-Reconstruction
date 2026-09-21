"use client";

import React, { useEffect, useState } from "react";
import {
  Building2,
  Maximize2,
  Box,
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
} from "lucide-react";
import { BuildingInstance, MissionDetail, SemanticQualityReport } from "@/types/mission";

interface StructureInspectorProps {
  buildings: BuildingInstance[];
  detail?: MissionDetail | null;
  semanticQuality?: SemanticQualityReport;
  selectedBuildingId?: number | null;
  onFocusBuilding?: (bldg: BuildingInstance) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  Building: "#3b82f6",
  Tree: "#22c55e",
  Road: "#64748b",
  "Background clutter": "#a855f7",
  Background: "#a855f7",
  "Low vegetation": "#84cc16",
  "Low Vegetation": "#84cc16",
  "Moving car": "#f97316",
  Human: "#ef4444",
};

export const StructureInspector: React.FC<StructureInspectorProps> = ({
  buildings,
  detail,
  semanticQuality,
  selectedBuildingId,
  onFocusBuilding,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Stay in sync when the 3D scene drives selection (a building clicked in Cesium
  // posts its instance_id up to the parent, which flows back down here).
  useEffect(() => {
    if (selectedBuildingId == null) return;
    const idx = buildings.findIndex((b) => b.instance_id === selectedBuildingId);
    if (idx >= 0) setSelectedIndex(idx);
  }, [selectedBuildingId, buildings]);

  const selectedBuilding = buildings[selectedIndex] || buildings[0] || null;

  const breakdown = detail?.report?.class_breakdown || [];
  const totalPoints = breakdown.reduce((sum, c) => sum + c.n_points, 0);
  const categories = totalPoints > 0
    ? breakdown
        .map((c) => ({
          name: c.class_name,
          pct: (c.n_points / totalPoints) * 100,
          color: CATEGORY_COLORS[c.class_name] || "#71717a",
        }))
        .sort((a, b) => b.pct - a.pct)
    : [];

  return (
    <aside className="w-80 border-l border-zinc-800 bg-zinc-950 flex flex-col h-full overflow-y-auto shrink-0 select-none text-xs">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-emerald-400" />
            <span className="font-semibold text-zinc-200">Structure Inspector</span>
          </div>
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
            {buildings.length} Structures
          </span>
        </div>
        <p className="text-[10px] text-zinc-400 leading-tight">
          Discrete architectural entities isolated via spatial DBSCAN clustering on building-classified point tracks.
        </p>

        {/* Building selector pills */}
        {buildings.length > 0 && (
          <div className="flex gap-1.5 pt-1 overflow-x-auto pb-1">
            {buildings.map((b, idx) => (
              <button
                key={b.instance_id}
                onClick={() => {
                  setSelectedIndex(idx);
                  onFocusBuilding?.(b);
                }}
                className={`px-3 py-1 rounded text-[11px] font-medium transition-all shrink-0 ${
                  selectedIndex === idx
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "bg-zinc-900 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 border border-zinc-800"
                }`}
              >
                Structure #{b.instance_id}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected Building Details */}
      {selectedBuilding ? (
        <div className="p-4 space-y-4 border-b border-zinc-800">
          <div className="flex items-center justify-between">
            <span className="text-zinc-200 font-bold text-sm">
              Structure #{selectedBuilding.instance_id}
            </span>
            {onFocusBuilding && (
              <button
                onClick={() => onFocusBuilding(selectedBuilding)}
                className="flex items-center gap-1 text-[10px] text-emerald-400 hover:text-emerald-300 font-mono"
              >
                <Maximize2 className="w-3 h-3" /> Focus View
              </button>
            )}
          </div>

          {/* Metric Cards Grid */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-zinc-900/90 p-2.5 rounded border border-zinc-800">
              <div className="text-[10px] text-zinc-500 flex items-center gap-1">
                <Box className="w-3 h-3 text-blue-400" />
                Footprint Area
              </div>
              <div className="text-base font-bold text-zinc-100 font-mono mt-0.5">
                {selectedBuilding.footprint_area_m2.toFixed(2)} m²
              </div>
              <div className="text-[9px] text-zinc-500">2D Convex Hull</div>
            </div>

            <div className="bg-zinc-900/90 p-2.5 rounded border border-zinc-800">
              <div className="text-[10px] text-zinc-500 flex items-center gap-1">
                <Layers className="w-3 h-3 text-amber-400" />
                Height (ΔZ)
              </div>
              <div className="text-base font-bold text-zinc-100 font-mono mt-0.5">
                {selectedBuilding.height_m.toFixed(2)} m
              </div>
              <div className="text-[9px] text-zinc-500">Peak: {selectedBuilding.peak_elevation_m.toFixed(1)}m</div>
            </div>

            <div className="bg-zinc-900/90 p-2.5 rounded border border-zinc-800">
              <div className="text-[10px] text-zinc-500 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-purple-400" />
                Volume Estimate
              </div>
              <div className="text-base font-bold text-emerald-400 font-mono mt-0.5">
                {selectedBuilding.volume_m3.toFixed(1)} m³
              </div>
              <div className="text-[9px] text-zinc-500">Prism × 0.85 fill</div>
            </div>

            <div className="bg-zinc-900/90 p-2.5 rounded border border-zinc-800">
              <div className="text-[10px] text-zinc-500 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                Confidence
              </div>
              <div className="text-base font-bold text-zinc-100 font-mono mt-0.5">
                {(selectedBuilding.mean_confidence * 100).toFixed(1)}%
              </div>
              <div className="text-[9px] text-zinc-500">{selectedBuilding.point_count.toLocaleString()} points</div>
            </div>
          </div>

          {/* Spatial Coordinates */}
          <div className="bg-zinc-900/60 p-2 rounded border border-zinc-800 text-[10px] space-y-1 font-mono text-zinc-400">
            <div>Centroid (ENU): [{selectedBuilding.centroid_xyz.join(", ")}]</div>
            <div>Base Elevation: {selectedBuilding.base_elevation_m.toFixed(2)} m</div>
          </div>
        </div>
      ) : (
        <div className="p-6 text-center text-zinc-500 text-xs">
          No discrete structures detected in this flight sector.
        </div>
      )}

      {/* Semantic Category Breakdown */}
      <div className="p-4 space-y-3 flex-1">
        <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono flex items-center gap-1.5 font-medium">
          <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
          Scene Semantic Composition
        </div>

        {categories.length > 0 ? (
          <div className="space-y-2">
            {categories.map((cat) => (
              <div key={cat.name} className="space-y-0.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-zinc-300 font-medium">{cat.name}</span>
                  <span className="font-mono text-zinc-400">{cat.pct.toFixed(1)}%</span>
                </div>
                <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${cat.pct}%`, backgroundColor: cat.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[10px] text-zinc-600">No class breakdown available for this mission.</p>
        )}

        {/* Quality summary alert — reflects the actual semantic quality tier from the
            pipeline, not an unconditional "verified" claim. High multi-view agreement
            does not by itself mean the class labels are correct. */}
        {semanticQuality && semanticQuality.quality_tier === "TRUSTED" ? (
          <div className="mt-4 p-2.5 rounded bg-emerald-950/40 border border-emerald-800/40 text-[10px] text-emerald-300 space-y-1">
            <div className="font-semibold flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3 h-3" />
              Verified Geometry Consensus
            </div>
            <p className="text-zinc-400 leading-tight">{semanticQuality.summary}</p>
          </div>
        ) : semanticQuality ? (
          <div className="mt-4 p-2.5 rounded bg-red-950/40 border border-red-800/40 text-[10px] text-red-300 space-y-1">
            <div className="font-semibold flex items-center gap-1 text-red-400">
              <AlertTriangle className="w-3 h-3" />
              {semanticQuality.quality_tier.replace("_", " ")}
            </div>
            <p className="text-zinc-400 leading-tight">{semanticQuality.summary}</p>
          </div>
        ) : null}
      </div>
    </aside>
  );
};
