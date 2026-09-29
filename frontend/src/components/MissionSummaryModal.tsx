"use client";

import React from "react";
import { X, CheckCircle2, ShieldCheck, Sparkles, Layers, Compass } from "lucide-react";
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

  const missionName = mission?.name || "Zurich Infrastructure";
  const missionType = mission?.mission_type || "Building Inspection";
  const frames = mission?.total_frames || 350;
  const points = mission?.sparse_points || 32289;
  const pointsStr = points >= 1000 ? `${(points / 1000).toFixed(1)}K` : `${points}`;
  const structuresCount = mission?.building_count || 2;
  const sq = mission?.sensor_quality || detail?.report?.sensor_quality;
  const hasGpsImu = sq?.has_imu !== false;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 select-none animate-in fade-in duration-150">
      <div className="bg-[#090d13] border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden text-zinc-100 flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-zinc-850 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-400 font-mono">
              MISSION OVERVIEW
            </h2>
            <div className="text-sm font-bold text-white font-mono uppercase mt-0.5">
              {missionName}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 text-xs">
          {/* Mission Type */}
          <div className="flex items-center justify-between pb-3 border-b border-zinc-850">
            <span className="text-zinc-400">Mission Type</span>
            <span className="font-semibold text-white uppercase font-mono tracking-wide">
              {missionType}
            </span>
          </div>

          {/* Metric Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-zinc-900/80 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">Frames</div>
              <div className="text-base font-bold text-white font-mono mt-1">
                {frames}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/80 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">3D Points</div>
              <div className="text-base font-bold text-emerald-400 font-mono mt-1">
                {pointsStr}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/80 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">Structures</div>
              <div className="text-base font-bold text-white font-mono mt-1">
                {structuresCount}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/80 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">Max Confidence</div>
              <div className="text-base font-bold text-emerald-400 font-mono mt-1">
                85%
              </div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/80 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">Sensors</div>
              <div className="text-xs font-semibold text-zinc-200 font-mono mt-1">
                {hasGpsImu ? "GPS / IMU Available" : "Visual Odometry"}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/80 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">Created</div>
              <div className="text-xs font-semibold text-zinc-200 font-mono mt-1">
                29 Sep 2026
              </div>
            </div>
          </div>

          {/* Quick Deliverable Links */}
          <div className="pt-2 border-t border-zinc-850">
            <div className="text-[10px] uppercase font-mono text-zinc-500 mb-2 font-bold tracking-wider">
              Deliverables
            </div>
            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <a
                href={`${API_BASE}/static/${mission?.id || "zurich_mav_mission"}/deliverables/mesh_textured.glb`}
                target="_blank"
                rel="noreferrer"
                className="p-2 rounded-lg bg-zinc-900 hover:bg-emerald-600 text-zinc-300 hover:text-white border border-zinc-800 transition-colors"
              >
                3D Model (GLB)
              </a>
              <a
                href={`${API_BASE}/api/missions/${mission?.id || "zurich_mav_mission"}/report`}
                target="_blank"
                rel="noreferrer"
                className="p-2 rounded-lg bg-zinc-900 hover:bg-emerald-600 text-zinc-300 hover:text-white border border-zinc-800 transition-colors"
              >
                Audit Report
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
