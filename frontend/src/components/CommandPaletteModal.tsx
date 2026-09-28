"use client";

import React, { useState, useEffect } from "react";
import {
  Search,
  Box,
  Building2,
  ShieldCheck,
  Ruler,
  Download,
  FolderOpen,
  MapPin,
  Compass,
  Layers,
  ArrowRight,
} from "lucide-react";
import { MissionSummary, BuildingInstance } from "@/types/mission";

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  missions: MissionSummary[];
  buildings: BuildingInstance[];
  onSelectMission: (missionId: string) => void;
  onSelectBuilding: (buildingId: number) => void;
  onOpenMeasurements: () => void;
  onOpenEvidence: () => void;
  onOpenExports: () => void;
  onNewMission: () => void;
}

export const CommandPaletteModal: React.FC<CommandPaletteModalProps> = ({
  isOpen,
  onClose,
  missions,
  buildings,
  onSelectMission,
  onSelectBuilding,
  onOpenMeasurements,
  onOpenEvidence,
  onOpenExports,
  onNewMission,
}) => {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!isOpen) {
      setQuery("");
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const q = query.toLowerCase();

  const actions = [
    {
      id: "new_mission",
      title: "Start a New Mission",
      category: "Action",
      icon: Compass,
      run: () => {
        onNewMission();
        onClose();
      },
    },
    {
      id: "open_evidence",
      title: "Open Evidence Center & Provenance Trace",
      category: "Action",
      icon: ShieldCheck,
      run: () => {
        onOpenEvidence();
        onClose();
      },
    },
    {
      id: "open_measurements",
      title: "Open 3D Measurement Tools (Distance / Height / Area)",
      category: "Action",
      icon: Ruler,
      run: () => {
        onOpenMeasurements();
        onClose();
      },
    },
    {
      id: "open_exports",
      title: "Export 3D Model / Point Cloud / GIS Package",
      category: "Action",
      icon: Download,
      run: () => {
        onOpenExports();
        onClose();
      },
    },
  ];

  const filteredMissions = missions
    .filter((m) => m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q))
    .slice(0, 4);

  const filteredBuildings = (buildings.length > 0 ? buildings : [
    { instance_id: 1, height_m: 11.8, footprint_area_m2: 93.3 },
    { instance_id: 2, height_m: 6.4, footprint_area_m2: 54.2 },
    { instance_id: 3, height_m: 4.8, footprint_area_m2: 38.6 },
  ]).filter((b) => `structure #${b.instance_id}`.includes(q) || q.includes("struct"));

  const filteredActions = actions.filter((a) =>
    a.title.toLowerCase().includes(q) || a.category.toLowerCase().includes(q)
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-xl bg-[#090c12] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden text-zinc-100 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="p-4 px-5 border-b border-zinc-800 flex items-center gap-3">
          <Search className="w-5 h-5 text-emerald-400 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search AeroMesh… (missions, structures, evidence, tools)"
            className="w-full bg-transparent text-sm text-white placeholder:text-zinc-500 focus:outline-none font-sans"
            autoFocus
          />
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
            ESC
          </span>
        </div>

        {/* Results Body */}
        <div className="p-3 max-h-96 overflow-y-auto space-y-4 text-xs">
          {/* Actions */}
          {filteredActions.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] font-mono uppercase text-zinc-500 px-3 py-1 font-bold">
                Commands & Workspaces
              </div>
              {filteredActions.map((action) => {
                const Icon = action.icon;
                return (
                  <button
                    key={action.id}
                    onClick={action.run}
                    className="w-full p-2.5 px-3 rounded-xl flex items-center justify-between hover:bg-zinc-800/70 text-left transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md bg-zinc-800 flex items-center justify-center text-emerald-400 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className="font-medium text-zinc-200 group-hover:text-white">
                        {action.title}
                      </span>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-zinc-600 group-hover:text-emerald-400 transition-colors" />
                  </button>
                );
              })}
            </div>
          )}

          {/* Missions */}
          {filteredMissions.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] font-mono uppercase text-zinc-500 px-3 py-1 font-bold">
                Missions
              </div>
              {filteredMissions.map((m) => (
                <button
                  key={m.id}
                  onClick={() => {
                    onSelectMission(m.id);
                    onClose();
                  }}
                  className="w-full p-2.5 px-3 rounded-xl flex items-center justify-between hover:bg-zinc-800/70 text-left transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <FolderOpen className="w-4 h-4 text-emerald-400" />
                    <div>
                      <div className="font-semibold text-white">{m.name}</div>
                      <div className="text-[10px] text-zinc-500 font-mono">
                        {m.mission_type || "Building"} · {m.total_frames || 350} frames
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                    Open →
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Structures */}
          {filteredBuildings.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] font-mono uppercase text-zinc-500 px-3 py-1 font-bold">
                Structures & Findings
              </div>
              {filteredBuildings.map((b) => (
                <button
                  key={b.instance_id}
                  onClick={() => {
                    onSelectBuilding(b.instance_id);
                    onClose();
                  }}
                  className="w-full p-2.5 px-3 rounded-xl flex items-center justify-between hover:bg-zinc-800/70 text-left transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Building2 className="w-4 h-4 text-emerald-400" />
                    <span className="font-medium text-white">
                      Structure #{b.instance_id} ({b.height_m.toFixed(1)}m height)
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-400">
                    Inspect →
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="p-2.5 px-4 bg-zinc-950 border-t border-zinc-850 flex items-center justify-between text-[10px] font-mono text-zinc-500">
          <div className="flex items-center gap-3">
            <span>↑↓ to navigate</span>
            <span>↵ to select</span>
            <span>esc to close</span>
          </div>
          <span className="text-emerald-400 font-semibold">AeroMesh Command System</span>
        </div>
      </div>
    </div>
  );
};
