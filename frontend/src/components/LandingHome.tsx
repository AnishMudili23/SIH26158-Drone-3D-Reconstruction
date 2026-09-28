"use client";

import React, { useState } from "react";
import {
  Compass,
  ArrowRight,
  FolderOpen,
  Play,
  Layers,
  Sparkles,
  Download,
  Building2,
  Cpu,
  ShieldCheck,
  CheckCircle2,
  Box,
  MapPin,
  HardHat,
  Map,
  Activity,
  Microscope,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { MissionSummary } from "@/types/mission";
import { Hero3DCanvas } from "./Hero3DCanvas";
import { PersonaDetailModal, PersonaId } from "./PersonaDetailModal";

interface LandingHomeProps {
  missions: MissionSummary[];
  onStartMission: (initialType?: string) => void;
  onExploreDemo: () => void;
  onOpenMission: (missionId: string) => void;
  onOpenMissionManager?: () => void;
  onClearDemoData?: () => void;
}

const PERSONAS = [
  {
    id: "infrastructure" as PersonaId,
    icon: HardHat,
    title: "Infrastructure",
    desc: "Inspect bridges, buildings, roads and critical assets using drone-derived 3D reconstruction.",
    focus: "Structures · Damage · Measurements · Evidence",
  },
  {
    id: "survey" as PersonaId,
    icon: Map,
    title: "Survey & Mapping",
    desc: "Generate survey-grade geospatial DSM, DTM, and GIS-ready orthomosaics with verified ground accuracy.",
    focus: "Orthomosaic · DSM · DTM · GIS Export",
  },
  {
    id: "disaster" as PersonaId,
    icon: Activity,
    title: "Disaster Response",
    desc: "Quickly reconstruct affected areas, identify clear routes, and assess damage.",
    focus: "Rapid 3D · Affected Area · Access Routes",
  },
  {
    id: "research" as PersonaId,
    icon: Microscope,
    title: "Research & Inspection",
    desc: "Analyze multi-view geometry, camera observations, bundle adjustment uncertainty, and scientific point clouds.",
    focus: "Point Cloud · Trajectory · Uncertainty",
  },
];

export const LandingHome: React.FC<LandingHomeProps> = ({
  missions,
  onStartMission,
  onExploreDemo,
  onOpenMission,
  onOpenMissionManager,
  onClearDemoData,
}) => {
  const [activePersonaModal, setActivePersonaModal] = useState<PersonaId | null>(null);
  const [showAdminTools, setShowAdminTools] = useState(false);
  const [missionPage, setMissionPage] = useState(1);
  const missionsPerPage = 4;

  const totalMissionPages = Math.max(1, Math.ceil(missions.length / missionsPerPage));
  const currentPageClamped = Math.min(missionPage, totalMissionPages);
  const pagedMissions = missions.slice(
    (currentPageClamped - 1) * missionsPerPage,
    currentPageClamped * missionsPerPage
  );

  return (
    <div className="flex-1 overflow-y-auto bg-[#05070a] text-zinc-100 flex flex-col justify-between selection:bg-emerald-600/30">
      <div className="relative isolate px-6 pt-10 pb-16 lg:px-8 max-w-6xl mx-auto w-full">
        {/* 1. Hero Statement & Mission Actions */}
        <div className="text-center max-w-3xl mx-auto pt-2 pb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-500/30 bg-emerald-950/40 text-emerald-400 text-xs font-mono uppercase tracking-wider mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            AeroMesh Platform
          </div>

          <h1 className="text-4xl sm:text-6xl font-bold tracking-tight text-white mb-4 leading-tight">
            Turn aerial video into a{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-green-400">
              world you can measure.
            </span>
          </h1>

          <p className="text-sm sm:text-base font-mono uppercase tracking-widest text-zinc-400 mb-8">
            Reconstruct. Understand. Verify.
          </p>

          {/* Primary Actions */}
          <div className="flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={() => onStartMission()}
              className="flex items-center gap-2.5 px-6 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm shadow-lg shadow-emerald-600/25 transition-all transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
            >
              <Compass className="w-4 h-4" />
              <span>Start a Mission</span>
              <ArrowRight className="w-4 h-4 text-emerald-200" />
            </button>

            <button
              onClick={onExploreDemo}
              className="flex items-center gap-2 px-5 py-3.5 rounded-xl bg-zinc-900/90 hover:bg-zinc-800 text-zinc-200 font-semibold text-sm border border-zinc-750 transition-all cursor-pointer"
            >
              <Play className="w-4 h-4 text-emerald-400" />
              <span>Explore a Demo</span>
            </button>

            {onOpenMissionManager && (
              <button
                onClick={onOpenMissionManager}
                className="flex items-center gap-2 px-5 py-3.5 rounded-xl bg-zinc-900/90 hover:bg-zinc-800 text-zinc-200 font-semibold text-sm border border-zinc-750 transition-all cursor-pointer"
              >
                <FolderOpen className="w-4 h-4 text-zinc-400" />
                <span>Open Existing Mission</span>
              </button>
            )}
          </div>
        </div>

        {/* 2. Living 3D Visual Hero */}
        <div className="my-6">
          <Hero3DCanvas />
        </div>

        {/* 3. Credible Data Quality Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-8">
          <div className="p-3 rounded-xl border border-zinc-850 bg-zinc-900/40 text-center">
            <div className="text-[10px] text-zinc-500 font-mono uppercase">Positioning</div>
            <div className="text-xs font-semibold text-white mt-0.5">GPS / RTK Synced</div>
          </div>
          <div className="p-3 rounded-xl border border-zinc-850 bg-zinc-900/40 text-center">
            <div className="text-[10px] text-zinc-500 font-mono uppercase">Attitude Tracking</div>
            <div className="text-xs font-semibold text-white mt-0.5">IMU Orientation</div>
          </div>
          <div className="p-3 rounded-xl border border-zinc-850 bg-zinc-900/40 text-center">
            <div className="text-[10px] text-zinc-500 font-mono uppercase">Keyframes</div>
            <div className="text-xs font-semibold text-emerald-400 mt-0.5">350 Aligned (0 blur)</div>
          </div>
          <div className="p-3 rounded-xl border border-zinc-850 bg-zinc-900/40 text-center">
            <div className="text-[10px] text-zinc-500 font-mono uppercase">Defensibility</div>
            <div className="text-xs font-semibold text-emerald-400 mt-0.5">Evidence-Backed</div>
          </div>
        </div>

        {/* 4. Personas: "Who are you using AeroMesh for?" (Interactive Context Modals) */}
        <div className="my-12">
          <div className="text-center max-w-xl mx-auto mb-6">
            <h2 className="text-xl font-bold text-white mb-1.5">
              Who are you using AeroMesh for?
            </h2>
            <p className="text-xs text-zinc-400">
              Click any profile to explore typical workflows, specialized layers, and available tools.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {PERSONAS.map((p) => {
              const Icon = p.icon;
              return (
                <div
                  key={p.id}
                  onClick={() => setActivePersonaModal(p.id)}
                  className="p-5 rounded-2xl border border-zinc-800 bg-zinc-900/50 hover:bg-zinc-850 hover:border-emerald-500/60 transition-all cursor-pointer flex flex-col justify-between group shadow-sm hover:shadow-emerald-950/20"
                >
                  <div>
                    <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-3.5 group-hover:scale-105 transition-transform">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="text-sm font-bold text-white mb-1 group-hover:text-emerald-300 transition-colors">
                      {p.title}
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-relaxed mb-4">{p.desc}</p>
                  </div>
                  <div className="pt-3 border-t border-zinc-800/80 flex items-center justify-between text-[10px] font-mono text-emerald-400">
                    <span className="truncate pr-1">{p.focus}</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform shrink-0" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 5. Recent Missions (Requirement #19) */}
        <div className="mt-10 pt-8 border-t border-zinc-850">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-300">
                Recent Missions
              </h3>
              <p className="text-xs text-zinc-500">
                Select an operational flight to inspect in the 3D studio
              </p>
            </div>
            {onOpenMissionManager && (
              <button
                onClick={onOpenMissionManager}
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-colors cursor-pointer"
              >
                <span>View all missions</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {pagedMissions.map((m) => (
              <div
                key={m.id}
                onClick={() => onOpenMission(m.id)}
                className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800/80 hover:border-emerald-500/50 transition-all cursor-pointer flex items-center justify-between group"
              >
                <div className="space-y-1 min-w-0 pr-3">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-zinc-200 text-sm truncate group-hover:text-emerald-300 transition-colors">
                      {m.name}
                    </span>
                    {m.is_demo && (
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 border border-zinc-750">
                        SIMULATED
                      </span>
                    )}
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40 font-semibold">
                      ● READY
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono">
                    <span>{m.mission_type || "Building"}</span>
                    <span>·</span>
                    <span>{m.total_frames || 350} frames</span>
                    <span>·</span>
                    <span>{m.building_count || 3} structures</span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 group-hover:translate-x-1 transition-transform shrink-0">
                  <span>Open</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>
            ))}
          </div>

          {/* Smooth Pagination Bar */}
          {totalMissionPages > 1 && (
            <div className="mt-4 flex items-center justify-between text-xs font-mono text-zinc-400 border-t border-zinc-850/60 pt-3">
              <span className="text-zinc-500 text-[11px]">
                Showing {(currentPageClamped - 1) * missionsPerPage + 1}–{Math.min(currentPageClamped * missionsPerPage, missions.length)} of {missions.length} missions
              </span>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setMissionPage((p) => Math.max(1, p - 1))}
                  disabled={currentPageClamped <= 1}
                  className="px-2.5 py-1 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-40 disabled:hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors cursor-pointer disabled:cursor-not-allowed"
                >
                  ← Prev
                </button>

                <div className="flex items-center gap-1">
                  {Array.from({ length: totalMissionPages }, (_, i) => i + 1).map((num) => (
                    <button
                      key={num}
                      onClick={() => setMissionPage(num)}
                      className={`w-6 h-6 rounded-md text-[11px] font-mono flex items-center justify-center transition-colors cursor-pointer ${
                        currentPageClamped === num
                          ? "bg-emerald-600 text-white font-bold"
                          : "bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800"
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => setMissionPage((p) => Math.min(totalMissionPages, p + 1))}
                  disabled={currentPageClamped >= totalMissionPages}
                  className="px-2.5 py-1 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-40 disabled:hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors cursor-pointer disabled:cursor-not-allowed"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 6. Admin / Developer Data Reset Section (Requirement #20) */}
        <div className="mt-12 pt-6 border-t border-zinc-900">
          <div className="flex items-center justify-between text-xs text-zinc-600 mb-2">
            <button
              onClick={() => setShowAdminTools(!showAdminTools)}
              className="text-[11px] font-mono text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
            >
              {showAdminTools ? "▲ Hide Data Management" : "▼ Developer / Data Management"}
            </button>
          </div>

          {showAdminTools && (
            <div className="p-4 rounded-xl border border-zinc-850 bg-zinc-950/80 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-zinc-300 font-mono uppercase text-[11px]">
                    DATA MANAGEMENT
                  </div>
                  <div className="text-[11px] text-zinc-500">
                    Manage demonstration and scratch reconstruction runs
                  </div>
                </div>
                <span className="text-[10px] text-amber-500 font-mono">
                  ⚠ Admin controls
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={onExploreDemo}
                  className="px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-medium cursor-pointer"
                >
                  Load Demo Data
                </button>
                <button
                  onClick={onClearDemoData}
                  className="px-3 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/60 border border-red-900/60 text-red-300 text-xs font-medium cursor-pointer"
                >
                  Clear Demo Missions
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 7. Subtle "Powered by" Footer */}
      <footer className="border-t border-zinc-900 py-6 px-6 text-center bg-[#030508]">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-500">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-zinc-400">AEROMESH</span>
            <span>·</span>
            <span>Turn aerial video into a world you can measure.</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[11px] font-mono text-zinc-400">
            <span className="text-zinc-600 font-sans">Powered by:</span>
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
      </footer>

      {/* Persona Detail Modal */}
      <PersonaDetailModal
        isOpen={!!activePersonaModal}
        onClose={() => setActivePersonaModal(null)}
        personaId={activePersonaModal}
        onStartMission={(initialType) => onStartMission(initialType)}
        onExploreDemo={onExploreDemo}
      />
    </div>
  );
};
