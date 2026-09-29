"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Satellite,
  ShieldCheck,
  Cpu,
  RefreshCw,
  Layers,
  Plus,
  Home,
  Compass,
  CheckCircle2,
  HardDrive,
  Activity,
  X,
  Ruler,
  FolderDown,
  Search,
} from "lucide-react";
import { MissionSummary, SensorQualityReport } from "@/types/mission";

interface HeaderProps {
  missions: MissionSummary[];
  selectedMissionId: string;
  onSelectMission: (id: string) => void;
  onNewMission?: () => void;
  onOpenMissionsModal?: () => void;
  onOpenSearch?: () => void;
  viewMode?: "home" | "studio";
  onViewModeChange?: (mode: "home" | "studio") => void;
  activeTab?: "workspace" | "evidence" | "measurements" | "exports";
  onTabChange?: (tab: "workspace" | "evidence" | "measurements" | "exports") => void;
  sensorQuality?: SensorQualityReport;
  systemHealth?: { status: string; gpu_available: boolean; device: string };
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  missions,
  selectedMissionId,
  onSelectMission,
  onNewMission,
  onOpenMissionsModal,
  onOpenSearch,
  viewMode = "studio",
  onViewModeChange,
  activeTab = "workspace",
  onTabChange,
  sensorQuality,
  systemHealth,
  onRefresh,
}) => {
  const [isSystemMenuOpen, setIsSystemMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close system menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsSystemMenuOpen(false);
      }
    };
    if (isSystemMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isSystemMenuOpen]);

  const myMissions = missions.filter(
    (m) => m.category === "MY_MISSIONS" || (!m.is_demo && m.id !== "zurich_mav_mission")
  );
  const demoMissions = missions.filter(
    (m) => m.category === "DEMO_MISSIONS" || m.is_demo || m.id === "zurich_mav_mission"
  );

  return (
    <header className="h-14 border-b border-zinc-850 bg-[#05070a] px-5 flex items-center justify-between shrink-0 select-none z-30">
      {/* 1. Left: Brand & Main Section Navigation */}
      <div className="flex items-center gap-8">
        <div
          onClick={() => onViewModeChange?.("home")}
          className="flex items-center gap-2 cursor-pointer group"
        >
          <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold group-hover:scale-105 transition-transform">
            <Layers className="w-4 h-4" />
          </div>
          <span className="text-sm tracking-wider uppercase font-mono font-bold text-white group-hover:text-emerald-400 transition-colors">
            AEROMESH
          </span>
        </div>

        {/* Clean Top Navigation Links */}
        <nav className="hidden md:flex items-center gap-1 text-xs font-medium">
          <button
            onClick={() => {
              if (onOpenMissionsModal) {
                onOpenMissionsModal();
              } else {
                onViewModeChange?.("home");
              }
            }}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              viewMode === "home"
                ? "bg-zinc-800 text-white font-semibold"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            Missions
          </button>

          <button
            onClick={() => {
              onViewModeChange?.("studio");
              onTabChange?.("workspace");
            }}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              viewMode === "studio" && activeTab === "workspace"
                ? "bg-zinc-800 text-white font-semibold"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            Workspace
          </button>

          <button
            onClick={() => {
              onTabChange?.("evidence");
            }}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              viewMode === "studio" && activeTab === "evidence"
                ? "bg-zinc-800 text-white font-semibold"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            Evidence
          </button>

          <button
            onClick={() => {
              onTabChange?.("measurements");
            }}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              viewMode === "studio" && activeTab === "measurements"
                ? "bg-zinc-800 text-white font-semibold"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            Measurements
          </button>

          <button
            onClick={() => {
              onTabChange?.("exports");
            }}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              viewMode === "studio" && activeTab === "exports"
                ? "bg-zinc-800 text-white font-semibold"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            Exports
          </button>
        </nav>
      </div>

      {/* 2. Center: Categorized Mission Selector (MY MISSIONS vs DEMO MISSIONS) */}
      <div className="hidden lg:flex items-center gap-3">
        {viewMode === "studio" && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500 font-medium">Mission:</span>
            <select
              value={selectedMissionId}
              onChange={(e) => onSelectMission(e.target.value)}
              aria-label="Select drone mission"
              className="bg-zinc-900 border border-zinc-750 text-zinc-200 text-xs rounded-lg px-2.5 py-1 font-medium focus:outline-none focus:border-emerald-500 transition-colors cursor-pointer max-w-[220px] truncate"
            >
              {myMissions.length > 0 && (
                <optgroup label="MY MISSIONS">
                  {myMissions.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </optgroup>
              )}
              {demoMissions.length > 0 && (
                <optgroup label="DEMO MISSIONS">
                  {demoMissions.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>
        )}

        {/* Global Command / Search Trigger (Ctrl + K) */}
        {onOpenSearch && (
          <button
            onClick={onOpenSearch}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-850 border border-zinc-750 text-zinc-400 hover:text-zinc-200 text-xs transition-colors cursor-pointer font-sans"
            title="Search missions and commands (Ctrl + K)"
          >
            <Search className="w-3.5 h-3.5 text-zinc-500" />
            <span className="hidden xl:inline text-[11px]">Search…</span>
            <span className="font-mono text-[10px] text-zinc-500 bg-zinc-800 px-1 rounded ml-1">
              Ctrl K
            </span>
          </button>
        )}
      </div>

      {/* 3. Right: + New Mission & Clickable "● Ready" System Menu */}
      <div className="flex items-center gap-3">
        {onNewMission && (
          <button
            onClick={onNewMission}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors shadow-sm cursor-pointer"
            title="Start a new mission"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>+ New</span>
          </button>
        )}

        {/* System Ready Pill Popover Button */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setIsSystemMenuOpen(!isSystemMenuOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-850 border border-zinc-750 text-xs font-mono text-zinc-300 transition-colors cursor-pointer"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Ready</span>
          </button>

          {/* System Details Popover */}
          {isSystemMenuOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-xl border border-zinc-800 bg-[#0a0d13] p-4 shadow-2xl z-50 text-xs text-zinc-300 space-y-3">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                <span className="font-bold text-white uppercase tracking-wider text-[11px] font-mono">
                  System Status
                </span>
                <span className="text-[10px] text-emerald-400 font-mono">Operational</span>
              </div>

              <div className="space-y-2 text-[11px]">
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">GPU Acceleration</span>
                  <span className="font-mono text-white">
                    {systemHealth?.device || "RTX 3050"}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Processing Engine</span>
                  <span className="text-emerald-400 font-semibold font-mono">Ready</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Local Storage</span>
                  <span className="font-mono text-zinc-300">Fast NVMe</span>
                </div>
              </div>

              <div className="border-t border-zinc-800 pt-2.5 space-y-1.5">
                <div className="text-[10px] text-zinc-500 uppercase font-mono tracking-wider">
                  Sensors Connected
                </div>
                <div className="grid grid-cols-3 gap-1.5 font-mono text-[10px] text-center">
                  <div className="p-1 rounded bg-zinc-900 border border-zinc-800 text-emerald-400">
                    GPS ✓
                  </div>
                  <div className="p-1 rounded bg-zinc-900 border border-zinc-800 text-emerald-400">
                    IMU ✓
                  </div>
                  <div className="p-1 rounded bg-zinc-900 border border-zinc-800 text-emerald-400">
                    BARO ✓
                  </div>
                </div>
              </div>

              <div className="pt-1 flex justify-end">
                <button
                  onClick={() => {
                    onRefresh();
                    setIsSystemMenuOpen(false);
                  }}
                  className="text-[10px] text-zinc-400 hover:text-white flex items-center gap-1 font-mono cursor-pointer"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Check status</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
