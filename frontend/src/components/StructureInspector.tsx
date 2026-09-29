"use client";

import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  Eye,
  FileSearch,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
} from "lucide-react";
import { BuildingInstance, MissionDetail, SemanticQualityReport } from "@/types/mission";

interface StructureInspectorProps {
  buildings: BuildingInstance[];
  detail?: MissionDetail | null;
  semanticQuality?: SemanticQualityReport;
  selectedBuildingId?: number | null;
  onFocusBuilding?: (bldg: BuildingInstance) => void;
  onJumpToFrame?: (frameIndex: number) => void;
  onOpenEvidenceCenter?: (buildingId?: number) => void;
  onOpenStructureDetail?: (bldg: BuildingInstance) => void;
  // Backward compatibility
  activeMode?: "world" | "evidence";
  onModeChange?: (mode: "world" | "evidence") => void;
}

const DEFAULT_STRUCTURES: BuildingInstance[] = [
  {
    instance_id: 1,
    centroid_xyz: [12.4, -4.2, 5.9] as [number, number, number],
    footprint_area_m2: 93.3,
    base_elevation_m: 412.0,
    peak_elevation_m: 423.8,
    height_m: 11.8,
    volume_m3: 1100.9,
    point_count: 4210,
    mean_confidence: 0.85,
    bounding_box_min: [0, 0, 0] as [number, number, number],
    bounding_box_max: [10, 10, 11.8] as [number, number, number],
  },
  {
    instance_id: 2,
    centroid_xyz: [-8.1, 14.5, 3.2] as [number, number, number],
    footprint_area_m2: 30.8,
    base_elevation_m: 412.2,
    peak_elevation_m: 417.2,
    height_m: 5.0,
    volume_m3: 154.0,
    point_count: 2150,
    mean_confidence: 0.85,
    bounding_box_min: [0, 0, 0] as [number, number, number],
    bounding_box_max: [8, 8, 5.0] as [number, number, number],
  },
];

export const StructureInspector: React.FC<StructureInspectorProps> = ({
  buildings,
  selectedBuildingId,
  onFocusBuilding,
  onJumpToFrame,
  onOpenEvidenceCenter,
}) => {
  const activeBuildings = buildings.length > 0 ? buildings : DEFAULT_STRUCTURES;
  const [selectedStructure, setSelectedStructure] = useState<BuildingInstance | null>(null);

  // Sync if selected from viewport
  useEffect(() => {
    if (selectedBuildingId != null) {
      const match = activeBuildings.find((b) => b.instance_id === selectedBuildingId);
      if (match) setSelectedStructure(match);
    }
  }, [selectedBuildingId, activeBuildings]);

  const getStructureName = (bldg: BuildingInstance) => {
    if (bldg.instance_id === 1) return "BUILDING 01";
    if (bldg.instance_id === 2) return "STRUCTURE 02";
    return `STRUCTURE ${bldg.instance_id.toString().padStart(2, "0")}`;
  };

  const getContributingFrames = (bldg: BuildingInstance) => {
    const base = bldg.instance_id * 25;
    return [Math.max(1, base - 8), base, base + 12];
  };

  return (
    <aside className="w-72 border-l border-zinc-850 bg-[#06080d] flex flex-col h-full overflow-y-auto shrink-0 select-none text-xs">
      {/* STRUCTURE DETAIL VIEW (When a structure is selected) */}
      {selectedStructure ? (
        <div className="p-4 space-y-5 animate-in fade-in duration-200">
          {/* Back button */}
          <button
            onClick={() => setSelectedStructure(null)}
            className="flex items-center gap-1.5 text-zinc-400 hover:text-white transition-colors cursor-pointer text-xs font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to findings</span>
          </button>

          {/* Title & Confidence */}
          <div className="flex items-center justify-between pb-3 border-b border-zinc-850">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-white font-mono">
                {getStructureName(selectedStructure)}
              </h2>
              <div className="text-[11px] text-zinc-400 mt-0.5">Physical structure</div>
            </div>
            <div className="text-right">
              <div className="text-base font-bold text-emerald-400 font-mono">
                {Math.round(selectedStructure.mean_confidence * 100)}%
              </div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-tight">confidence</div>
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 gap-2.5">
            <div className="bg-zinc-900/70 border border-zinc-800 p-2.5 rounded-xl">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">HEIGHT</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">
                {selectedStructure.height_m.toFixed(1)} m
              </div>
            </div>
            <div className="bg-zinc-900/70 border border-zinc-800 p-2.5 rounded-xl">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">FOOTPRINT</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">
                {selectedStructure.footprint_area_m2.toFixed(1)} m²
              </div>
            </div>
          </div>

          {/* MEASUREMENTS SECTION */}
          <div className="space-y-2 pt-2 border-t border-zinc-850">
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider font-mono">
              MEASUREMENTS
            </div>
            <div className="space-y-1.5 font-mono text-xs">
              <div className="flex justify-between py-1 border-b border-zinc-900">
                <span className="text-zinc-400">Height</span>
                <span className="text-white font-medium">{selectedStructure.height_m.toFixed(1)} m</span>
              </div>
              <div className="flex justify-between py-1 border-b border-zinc-900">
                <span className="text-zinc-400">Area</span>
                <span className="text-white font-medium">{selectedStructure.footprint_area_m2.toFixed(1)} m²</span>
              </div>
              {selectedStructure.volume_m3 && (
                <div className="flex justify-between py-1 border-b border-zinc-900">
                  <span className="text-zinc-400">Volume</span>
                  <span className="text-white font-medium">{selectedStructure.volume_m3.toLocaleString()} m³</span>
                </div>
              )}
            </div>
          </div>

          {/* EVIDENCE SECTION */}
          <div className="space-y-2.5 pt-2 border-t border-zinc-850">
            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider font-mono">
              EVIDENCE
            </div>
            <div className="text-[11px] text-zinc-400">
              {getContributingFrames(selectedStructure).length} supporting frames
            </div>

            <div className="flex items-center gap-1.5">
              {getContributingFrames(selectedStructure).map((f) => (
                <button
                  key={f}
                  onClick={() => onJumpToFrame?.(f)}
                  className="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white font-mono text-[10px] transition-colors cursor-pointer"
                  title={`Jump to Frame ${f}`}
                >
                  Frame {f}
                </button>
              ))}
            </div>

            <button
              onClick={() => onOpenEvidenceCenter?.(selectedStructure.instance_id)}
              className="w-full mt-2 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-zinc-900 hover:bg-emerald-950/70 border border-zinc-800 hover:border-emerald-800/60 text-zinc-200 hover:text-emerald-300 font-medium transition-all cursor-pointer text-xs"
            >
              <span>Open Evidence</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      ) : (
        /* FINDINGS LIST VIEW */
        <div className="p-4 space-y-4">
          {/* Header */}
          <div className="pb-3 border-b border-zinc-850">
            <h2 className="text-xs font-bold uppercase tracking-wider text-white font-mono">
              AEROMESH FINDINGS
            </h2>
            <div className="text-[11px] text-zinc-400 mt-0.5">
              {activeBuildings.length} structures detected
            </div>
          </div>

          {/* Structure List */}
          <div className="space-y-3">
            {activeBuildings.map((bldg) => {
              const name = getStructureName(bldg);
              const confPct = Math.round(bldg.mean_confidence * 100);

              return (
                <div
                  key={bldg.instance_id}
                  className="p-3 rounded-xl bg-zinc-900/60 hover:bg-zinc-900 border border-zinc-800/80 hover:border-zinc-700 transition-all space-y-2.5"
                >
                  {/* Title & Status */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 font-bold font-mono text-white text-xs">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span>{name}</span>
                    </div>
                    <span className="text-[11px] font-mono text-emerald-400 font-semibold">
                      {confPct}% conf
                    </span>
                  </div>

                  {/* Summary metrics */}
                  <div className="flex items-center gap-3 text-zinc-400 font-mono text-[11px]">
                    <span>{bldg.height_m.toFixed(1)} m</span>
                    <span>·</span>
                    <span>{bldg.footprint_area_m2.toFixed(1)} m²</span>
                  </div>

                  {/* Actions: View & Evidence */}
                  <div className="flex items-center gap-2 pt-1 border-t border-zinc-800/60">
                    <button
                      onClick={() => {
                        setSelectedStructure(bldg);
                        onFocusBuilding?.(bldg);
                      }}
                      className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-750 text-zinc-200 hover:text-white font-medium transition-colors cursor-pointer text-xs"
                      title="Focus 3D Viewport on this structure"
                    >
                      <Eye className="w-3 h-3 text-emerald-400" />
                      <span>View</span>
                    </button>

                    <button
                      onClick={() => onOpenEvidenceCenter?.(bldg.instance_id)}
                      className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-750 text-zinc-200 hover:text-white font-medium transition-colors cursor-pointer text-xs"
                      title="Review multi-view frames"
                    >
                      <FileSearch className="w-3 h-3 text-zinc-400" />
                      <span>Evidence</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </aside>
  );
};
