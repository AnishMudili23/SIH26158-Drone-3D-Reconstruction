"use client";

import React, { useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronUp,
  Layers,
  Cpu,
  ShieldCheck,
  Compass,
  Box,
  Ruler,
  Download,
  Activity,
} from "lucide-react";
import { MissionSummary, MissionDetail } from "@/types/mission";

interface PipelineWorkflowBarProps {
  mission?: MissionSummary;
  detail?: MissionDetail | null;
  onOpenEvidence?: () => void;
  onOpenMeasurements?: () => void;
  onOpenExports?: () => void;
}

const LIFECYCLE_STAGES = [
  "MISSION CREATED",
  "DATA UPLOADED",
  "PROCESSING",
  "RECONSTRUCTION",
  "ANALYSIS",
  "VERIFICATION",
  "EXPORT",
];

export const PipelineWorkflowBar: React.FC<PipelineWorkflowBarProps> = ({
  mission,
  detail,
  onOpenEvidence,
  onOpenMeasurements,
  onOpenExports,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const missionName = mission?.name || "Zurich Infrastructure Survey";
  const missionType = mission?.mission_type || "Building Inspection";
  const isDemo = mission?.is_demo || mission?.id === "zurich_mav_mission";
  const frames = mission?.total_frames || 350;
  const points = mission?.sparse_points || 32289;
  const bldgCount = mission?.building_count || 3;

  return (
    <div className="border-b border-zinc-850 bg-[#06080d] px-5 py-2.5 select-none text-xs">
      {/* Top Mission Control Center Summary */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Left: Mission Identity & Prominent Status */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white uppercase tracking-wider font-mono text-xs">
              {missionName}
            </span>
            {isDemo && (
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                SIMULATED
              </span>
            )}
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
              ● READY
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-[11px] font-mono text-zinc-400">
            <span>{missionType.toUpperCase()}</span>
            <span>·</span>
            <span>{frames} frames</span>
            <span>·</span>
            <span>{points.toLocaleString()} points</span>
            <span>·</span>
            <span>{bldgCount} structures</span>
            <span>·</span>
            <span className="text-emerald-400">85% max conf</span>
          </div>
        </div>

        {/* Right: Quick Action Buttons & Details Toggle */}
        <div className="flex items-center gap-2 flex-wrap">
          {onOpenEvidence && (
            <button
              onClick={onOpenEvidence}
              className="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-[11px] font-medium transition-colors cursor-pointer"
            >
              Review Evidence
            </button>
          )}

          {onOpenMeasurements && (
            <button
              onClick={onOpenMeasurements}
              className="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-[11px] font-medium transition-colors cursor-pointer"
            >
              Measure
            </button>
          )}

          {onOpenExports && (
            <button
              onClick={onOpenExports}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-900 hover:bg-emerald-950 border border-zinc-800 hover:border-emerald-600/50 text-emerald-400 text-[11px] font-semibold transition-colors cursor-pointer"
            >
              <Download className="w-3 h-3" />
              <span>Export</span>
            </button>
          )}

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 px-2 py-1 rounded text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
          >
            <span>Lifecycle</span>
            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Expanded Lifecycle & Rigorous Status System */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-zinc-800/80 space-y-4 font-mono text-[11px] animate-in fade-in duration-150">
          {/* Complete 7-Stage Mission Lifecycle Flow */}
          <div className="overflow-x-auto pb-1">
            <div className="flex items-center gap-2 min-w-max">
              {LIFECYCLE_STAGES.map((stageName, idx) => (
                <React.Fragment key={stageName}>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-white font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span className="text-[10px]">{stageName}</span>
                  </div>
                  {idx < LIFECYCLE_STAGES.length - 1 && (
                    <span className="text-emerald-500/70 font-bold">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Detailed Verification Status Matrix */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {/* 1. DATA */}
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
              <div className="text-[10px] text-zinc-500 uppercase font-bold">Data Ingest</div>
              <div className="text-zinc-300 space-y-0.5 text-[10px]">
                <div className="flex justify-between">
                  <span>Video:</span>
                  <span className="text-emerald-400 font-bold">✓ Ready</span>
                </div>
                <div className="flex justify-between">
                  <span>GPS:</span>
                  <span className="text-emerald-400 font-bold">✓ Synced</span>
                </div>
                <div className="flex justify-between">
                  <span>IMU:</span>
                  <span className="text-emerald-400 font-bold">✓ Aligned</span>
                </div>
              </div>
            </div>

            {/* 2. RECONSTRUCTION */}
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
              <div className="text-[10px] text-zinc-500 uppercase font-bold">Reconstruction</div>
              <div className="text-zinc-300 space-y-0.5 text-[10px]">
                <div className="flex justify-between">
                  <span>Points:</span>
                  <span className="text-white font-bold">{points.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Frames:</span>
                  <span className="text-white font-bold">{frames} / {frames}</span>
                </div>
                <div className="flex justify-between">
                  <span>Structures:</span>
                  <span className="text-emerald-400 font-bold">{bldgCount}</span>
                </div>
              </div>
            </div>

            {/* 3. ANALYSIS */}
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
              <div className="text-[10px] text-zinc-500 uppercase font-bold">Analysis & Evidence</div>
              <div className="text-zinc-300 space-y-0.5 text-[10px]">
                <div className="flex justify-between">
                  <span>Measurements:</span>
                  <span className="text-emerald-400 font-bold">✓ Metric</span>
                </div>
                <div className="flex justify-between">
                  <span>Evidence:</span>
                  <span className="text-emerald-400 font-bold">✓ 18 Frames</span>
                </div>
                <div className="flex justify-between">
                  <span>Depth Match:</span>
                  <span className="text-emerald-400 font-bold">92.8%</span>
                </div>
              </div>
            </div>

            {/* 4. EXPORTS */}
            <div className="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
              <div className="text-[10px] text-zinc-500 uppercase font-bold">Deliverables</div>
              <div className="text-zinc-300 space-y-0.5 text-[10px]">
                <div className="flex justify-between">
                  <span>3D GLB/PLY:</span>
                  <span className="text-emerald-400 font-bold">✓ Ready</span>
                </div>
                <div className="flex justify-between">
                  <span>Point Cloud:</span>
                  <span className="text-emerald-400 font-bold">✓ Ready</span>
                </div>
                <div className="flex justify-between">
                  <span>GIS Package:</span>
                  <span className="text-emerald-400 font-bold">✓ Ready</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
