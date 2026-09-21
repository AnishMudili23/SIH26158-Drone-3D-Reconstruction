"use client";

import React from "react";
import {
  Satellite,
  ShieldAlert,
  ShieldCheck,
  Cpu,
  RefreshCw,
  Layers,
} from "lucide-react";
import { MissionSummary, SensorQualityReport } from "@/types/mission";

interface HeaderProps {
  missions: MissionSummary[];
  selectedMissionId: string;
  onSelectMission: (id: string) => void;
  sensorQuality?: SensorQualityReport;
  telemetryProvenance?: string;
  systemHealth?: { status: string; gpu_available: boolean; device: string };
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  missions,
  selectedMissionId,
  onSelectMission,
  sensorQuality,
  telemetryProvenance,
  systemHealth,
  onRefresh,
}) => {
  const provenanceBadge = (() => {
    switch (telemetryProvenance) {
      case "REAL":
        return { label: "PROVENANCE: REAL", cls: "bg-zinc-800/80 text-zinc-300 border-zinc-700/60" };
      case "SIMULATED":
        return { label: "PROVENANCE: SIMULATED", cls: "bg-amber-950/80 text-amber-400 border-amber-700/60" };
      case "ESTIMATED":
        return { label: "PROVENANCE: ESTIMATED (VISUAL ONLY)", cls: "bg-amber-950/80 text-amber-400 border-amber-700/60" };
      default:
        return { label: "PROVENANCE: NONE", cls: "bg-zinc-900 text-zinc-500 border-zinc-800" };
    }
  })();
  const getQualityBadge = () => {
    if (!sensorQuality) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-800 text-gray-300 border border-gray-700">
          <Satellite className="w-3.5 h-3.5 text-gray-400" />
          LOCAL METRIC
        </span>
      );
    }

    switch (sensorQuality.quality_tier) {
      case "STRONG_GPS":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-700/60 shadow-sm shadow-emerald-900/50">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            STRONG GPS (BNR {sensorQuality.baseline_to_noise_ratio.toFixed(1)})
          </span>
        );
      case "WEAK_GPS":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-700/60 shadow-sm shadow-amber-900/50">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            WEAK GPS (BNR {sensorQuality.baseline_to_noise_ratio.toFixed(2)})
          </span>
        );
      case "INSUFFICIENT_BASELINE":
        return (
          <span
            title={sensorQuality.summary}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-900/60 text-amber-300 border border-amber-600/80 cursor-help"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
            INSUFFICIENT BASELINE (BNR {sensorQuality.baseline_to_noise_ratio.toFixed(2)})
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-950/80 text-blue-400 border border-blue-700/60">
            <Satellite className="w-3.5 h-3.5 text-blue-400" />
            LOCAL METRIC
          </span>
        );
    }
  };

  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur px-4 flex items-center justify-between z-30 shrink-0 select-none">
      {/* Brand & Mission Selector */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs tracking-wider uppercase font-mono font-bold text-emerald-400">
              ANTIGRAVITY // 4D
            </div>
            <div className="text-[10px] text-zinc-400 tracking-tight leading-none">
              Single-Pass 3D Mission Digital Twin
            </div>
          </div>
        </div>

        <div className="h-4 w-px bg-zinc-800" />

        {/* Mission Switcher */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-medium">Mission:</span>
          <select
            value={selectedMissionId}
            onChange={(e) => onSelectMission(e.target.value)}
            aria-label="Select drone mission"
            className="bg-zinc-900 border border-zinc-700 text-zinc-200 text-xs rounded px-2.5 py-1 font-medium focus:outline-none focus:border-emerald-500 transition-colors"
          >
            {missions.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.total_frames || "?"} frames)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Sensor Quality & Diagnostics */}
      <div className="flex items-center gap-3">
        {getQualityBadge()}

        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono border ${provenanceBadge.cls}`}>
          {provenanceBadge.label}
        </span>

        <div className="h-4 w-px bg-zinc-800" />

        <div className="flex items-center gap-1.5 text-xs text-zinc-400 font-mono">
          <Cpu className="w-3.5 h-3.5 text-zinc-500" />
          <span className="hidden sm:inline">
            {systemHealth?.device || "RTX 3050 Laptop GPU"}
          </span>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        </div>

        <button
          onClick={onRefresh}
          title="Refresh Mission State"
          aria-label="Refresh mission state"
          className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
