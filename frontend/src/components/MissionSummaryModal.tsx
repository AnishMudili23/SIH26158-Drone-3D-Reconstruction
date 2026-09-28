"use client";

import React from "react";
import { X, CheckCircle2, Download, Eye, FileText, ShieldCheck, Sparkles } from "lucide-react";
import { MissionSummary, MissionDetail } from "@/types/mission";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface MissionSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  mission?: MissionSummary;
  detail?: MissionDetail | null;
}

export const MissionSummaryModal: React.FC<MissionSummaryModalProps> = ({
  isOpen,
  onClose,
  mission,
  detail,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#090d13] border border-zinc-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden text-zinc-100 flex flex-col">
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              Mission Summary
            </h2>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              {mission?.name || "Zurich Infrastructure Survey"} · Completed 28 Sep 2026
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 text-xs">
          {/* Key Metric Highlights */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div className="p-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-center">
              <div className="text-[10px] text-zinc-500 font-mono">Frames Processed</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">350 frames</div>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-center">
              <div className="text-[10px] text-zinc-500 font-mono">3D Points</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">32,289 pts</div>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-center">
              <div className="text-[10px] text-zinc-500 font-mono">Structures Found</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">3 verified</div>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-center">
              <div className="text-[10px] text-zinc-500 font-mono">Reconstruction Coverage</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">87%</div>
            </div>
          </div>

          {/* Key Findings */}
          <div className="space-y-1.5 p-3.5 rounded-xl bg-zinc-900/60 border border-zinc-800">
            <div className="font-semibold text-white uppercase text-[11px] font-mono">
              Key Findings
            </div>
            <p className="text-zinc-300 leading-relaxed text-[11px]">
              3 distinct physical structures were identified and reconstructed from multi-view observations. The primary building reaches an estimated elevation of 11.8 m with 85% multi-ray geometric consensus.
            </p>
          </div>

          {/* Data Quality */}
          <div className="space-y-1.5 p-3.5 rounded-xl bg-zinc-900/60 border border-zinc-800">
            <div className="font-semibold text-white uppercase text-[11px] font-mono">
              Data Quality & Georeferencing
            </div>
            <p className="text-zinc-300 leading-relaxed text-[11px]">
              GPS trajectory and camera frame alignment were successfully established without scale drift. Epipolar baseline geometry confirms 0.61 m horizontal RMSE.
            </p>
          </div>

          {/* Export Deliverables Grid */}
          <div className="space-y-2">
            <div className="font-semibold text-zinc-400 uppercase text-[10px] font-mono">
              Deliverables Ready
            </div>
            <div className="grid grid-cols-3 gap-2 text-center font-medium text-[11px]">
              <a
                href={`${API_BASE}/static/${mission?.id || "zurich_mav_mission"}/deliverables/mesh_textured.glb`}
                target="_blank"
                rel="noreferrer"
                className="p-2 rounded-lg bg-zinc-900 hover:bg-emerald-600 text-zinc-300 hover:text-white border border-zinc-800 transition-colors"
              >
                3D Model (GLB)
              </a>
              <a
                href={`${API_BASE}/static/${mission?.id || "zurich_mav_mission"}/deliverables/classified_pointcloud.las`}
                download
                className="p-2 rounded-lg bg-zinc-900 hover:bg-emerald-600 text-zinc-300 hover:text-white border border-zinc-800 transition-colors"
              >
                Point Cloud (LAS)
              </a>
              <a
                href={`${API_BASE}/api/missions/${mission?.id || "zurich_mav_mission"}/report`}
                target="_blank"
                rel="noreferrer"
                className="p-2 rounded-lg bg-zinc-900 hover:bg-emerald-600 text-zinc-300 hover:text-white border border-zinc-800 transition-colors"
              >
                Audit Report (HTML)
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
