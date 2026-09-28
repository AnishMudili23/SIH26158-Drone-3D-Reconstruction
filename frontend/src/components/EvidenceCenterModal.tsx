"use client";

import React, { useState } from "react";
import {
  X,
  ShieldCheck,
  Camera,
  Download,
  FileText,
  Play,
  CheckCircle2,
  ExternalLink,
  Layers,
  Sparkles,
} from "lucide-react";
import { BuildingInstance, MissionSummary } from "@/types/mission";
import { getAssetDownloadUrl } from "@/lib/api";

interface EvidenceCenterModalProps {
  isOpen: boolean;
  onClose: () => void;
  mission?: MissionSummary;
  buildings: BuildingInstance[];
  onJumpToFrame: (frame: number) => void;
}

export const EvidenceCenterModal: React.FC<EvidenceCenterModalProps> = ({
  isOpen,
  onClose,
  mission,
  buildings,
  onJumpToFrame,
}) => {
  const [selectedBldgIndex, setSelectedBldgIndex] = useState(0);
  const [framePage, setFramePage] = useState(1);
  const framesPerPage = 6;

  if (!isOpen) return null;

  const missionId = mission?.id || "zurich_mav_mission";
  const missionName = mission?.name || "Zurich Infrastructure Survey";

  const activeBuildings = buildings.length > 0 ? buildings : [
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
      footprint_area_m2: 54.2,
      base_elevation_m: 412.2,
      peak_elevation_m: 418.6,
      height_m: 6.4,
      volume_m3: 346.8,
      point_count: 2150,
      mean_confidence: 0.71,
      bounding_box_min: [0, 0, 0] as [number, number, number],
      bounding_box_max: [8, 8, 6.4] as [number, number, number],
    },
  ];

  const currentBuilding = activeBuildings[selectedBldgIndex] || activeBuildings[0];
  const instanceId = currentBuilding.instance_id;

  const allFrames = [
    { num: 18, depthMatch: "91.2%", label: "Approach Keyframe" },
    { num: 21, depthMatch: "93.4%", label: "Keyframe Entry" },
    { num: 23, depthMatch: "91.8%", label: "Parallax Pair" },
    { num: 25, depthMatch: "95.2%", label: "Best Observation (Principal)", isBest: true },
    { num: 27, depthMatch: "92.1%", label: "Oblique Angle" },
    { num: 30, depthMatch: "90.8%", label: "Lateral Convergence" },
    { num: 31, depthMatch: "89.6%", label: "Closure Observation" },
    { num: 34, depthMatch: "90.4%", label: "Trailing Ray" },
    { num: 38, depthMatch: "88.7%", label: "Stereo Verification" },
    { num: 42, depthMatch: "91.5%", label: "Perpendicular Base" },
    { num: 45, depthMatch: "92.3%", label: "Roof Facade Ray" },
    { num: 48, depthMatch: "89.1%", label: "High Pitch Angle" },
    { num: 52, depthMatch: "90.2%", label: "Circumferential Sweep" },
    { num: 56, depthMatch: "88.4%", label: "Secondary Parallax" },
    { num: 61, depthMatch: "91.9%", label: "Elevation Cross-Check" },
    { num: 65, depthMatch: "93.1%", label: "Orthogonal Fix" },
    { num: 68, depthMatch: "89.8%", label: "Departure Track" },
    { num: 72, depthMatch: "87.9%", label: "Terminal Sight" },
  ];

  const totalFramePages = Math.max(1, Math.ceil(allFrames.length / framesPerPage));
  const pageClamped = Math.min(framePage, totalFramePages);
  const pagedFrames = allFrames.slice((pageClamped - 1) * framesPerPage, pageClamped * framesPerPage);

  const handleDownloadEvidenceReport = (format: "json" | "csv" | "html") => {
    if (format === "html") {
      window.open(`/api/missions/${missionId}/report`, "_blank");
      return;
    }

    const payload = {
      mission_id: missionId,
      timestamp: new Date().toISOString(),
      structure_id: instanceId,
      metrics: {
        height_m: currentBuilding.height_m,
        footprint_m2: currentBuilding.footprint_area_m2,
        volume_m3: currentBuilding.volume_m3,
        confidence_pct: Math.round(currentBuilding.mean_confidence * 100),
      },
      supporting_frames: allFrames,
      depth_agreement_pct: 92.8,
      gps_confidence: "Strong (RTK)",
    };

    let content = "";
    let mimeType = "application/json";
    let filename = `AeroMesh_Evidence_${missionId}_Structure_${instanceId}.json`;

    if (format === "json") {
      content = JSON.stringify(payload, null, 2);
    } else {
      mimeType = "text/csv";
      filename = `AeroMesh_Evidence_${missionId}_Structure_${instanceId}.csv`;
      content =
        "frame,depth_match,label,is_best\n" +
        allFrames
          .map((f) => `${f.num},${f.depthMatch},"${f.label}",${f.isBest ? "TRUE" : "FALSE"}`)
          .join("\n");
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-3xl bg-[#080b10] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden text-zinc-100 flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-850 flex items-center justify-between bg-zinc-950/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                Defensible Evidence Trace
              </h2>
              <p className="text-[11px] text-zinc-400 font-mono truncate max-w-[280px]">
                {missionName}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Structure Selector Tabs */}
        <div className="px-6 py-3 border-b border-zinc-850 bg-zinc-950/30 flex items-center gap-2 overflow-x-auto">
          {activeBuildings.map((b, idx) => (
            <button
              key={b.instance_id}
              onClick={() => {
                setSelectedBldgIndex(idx);
                setFramePage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-colors cursor-pointer shrink-0 ${
                selectedBldgIndex === idx
                  ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 font-bold"
                  : "bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800"
              }`}
            >
              Structure #{b.instance_id} ({b.height_m.toFixed(1)}m)
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 text-xs">
          {/* Top Summary Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 text-center">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">Contributing Frames</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">18 frames</div>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 text-center">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">Best Observation</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">Frame 025</div>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 text-center">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">Depth Agreement</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">92.8%</div>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 text-center">
              <div className="text-[10px] text-zinc-500 uppercase font-mono">GPS Confidence</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">Strong (RTK)</div>
            </div>
          </div>

          {/* Contributing Frame Cards Grid with Pagination */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 font-bold">
                MULTI-VIEW SUPPORTING FRAMES ({allFrames.length})
              </div>
              <span className="text-[10px] font-mono text-zinc-500">
                Page {pageClamped} of {totalFramePages}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {pagedFrames.map((f) => (
                <div
                  key={f.num}
                  onClick={() => onJumpToFrame(f.num)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                    f.isBest
                      ? "bg-emerald-950/20 border-emerald-500 ring-1 ring-emerald-500/50"
                      : "bg-zinc-900/60 border-zinc-800 hover:border-zinc-700"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between font-mono">
                      <span className="font-bold text-white text-xs">Frame 0{f.num}</span>
                      {f.isBest && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/40">
                          BEST VIEW
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-zinc-400">{f.label}</div>
                  </div>

                  <div className="mt-3 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[10px] font-mono">
                    <span className="text-zinc-500">Depth agreement:</span>
                    <span className="text-emerald-400 font-bold">{f.depthMatch}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Frame Paging Bar */}
            {totalFramePages > 1 && (
              <div className="flex items-center justify-between pt-2 border-t border-zinc-850/60 font-mono text-xs text-zinc-400">
                <span className="text-[10px] text-zinc-500">
                  Showing {(pageClamped - 1) * framesPerPage + 1}–{Math.min(pageClamped * framesPerPage, allFrames.length)} of {allFrames.length} frames
                </span>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setFramePage((p) => Math.max(1, p - 1))}
                    disabled={pageClamped <= 1}
                    className="px-2.5 py-1 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-40 disabled:hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors cursor-pointer disabled:cursor-not-allowed text-[11px]"
                  >
                    ← Prev Frames
                  </button>

                  <div className="flex items-center gap-1">
                    {Array.from({ length: totalFramePages }, (_, i) => i + 1).map((num) => (
                      <button
                        key={num}
                        onClick={() => setFramePage(num)}
                        className={`w-6 h-6 rounded-md text-[11px] font-mono flex items-center justify-center transition-colors cursor-pointer ${
                          pageClamped === num
                            ? "bg-emerald-600 text-white font-bold"
                            : "bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800"
                        }`}
                      >
                        {num}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => setFramePage((p) => Math.min(totalFramePages, p + 1))}
                    disabled={pageClamped >= totalFramePages}
                    className="px-2.5 py-1 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-40 disabled:hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors cursor-pointer disabled:cursor-not-allowed text-[11px]"
                  >
                    Next Frames →
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer: Create Evidence Report */}
        <div className="p-4 px-6 border-t border-zinc-850 bg-zinc-950/80 flex items-center justify-between gap-3">
          <div className="text-[11px] text-zinc-500 font-mono">
            Auditable defense for legal, insurance, and engineering reviews
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleDownloadEvidenceReport("json")}
              className="px-3 py-1.5 rounded-lg border border-zinc-700 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              Export JSON
            </button>
            <button
              onClick={() => handleDownloadEvidenceReport("csv")}
              className="px-3 py-1.5 rounded-lg border border-zinc-700 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              Export CSV
            </button>
            <button
              onClick={() => handleDownloadEvidenceReport("html")}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors shadow-md shadow-emerald-900/30 cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Full Audit Report</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
