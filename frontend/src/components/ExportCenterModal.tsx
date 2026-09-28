"use client";

import React, { useState } from "react";
import {
  X,
  Download,
  FolderDown,
  Clock,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  FileCode,
  Layers,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { MissionSummary } from "@/types/mission";
import { getAssetDownloadUrl } from "@/lib/api";

interface ExportCenterModalProps {
  isOpen: boolean;
  onClose: () => void;
  mission?: MissionSummary;
}

export const ExportCenterModal: React.FC<ExportCenterModalProps> = ({
  isOpen,
  onClose,
  mission,
}) => {
  const [retrying, setRetrying] = useState(false);
  const [failedResolved, setFailedResolved] = useState(false);

  if (!isOpen) return null;

  const missionId = mission?.id || "zurich_mav_mission";
  const missionName = mission?.name || "Zurich Infrastructure Survey";

  const readyItems = [
    {
      id: "3d_glb",
      title: "3D Textured Mesh",
      type: "GLB",
      size: "2.8 MB",
      actionFormat: "glb",
    },
    {
      id: "3d_ply",
      title: "Polygon Mesh Geometry",
      type: "PLY",
      size: "3.4 MB",
      actionFormat: "ply",
    },
    {
      id: "pointcloud_las",
      title: "Classified Point Cloud",
      type: "LAS",
      size: "1.16 MB",
      actionFormat: "las",
    },
    {
      id: "dsm_geotiff",
      title: "Digital Surface Model (DSM)",
      type: "GeoTIFF",
      size: "4.3 KB",
      actionFormat: "dsm",
    },
    {
      id: "gis_full_package",
      title: "Complete GIS Package Archive",
      type: "ZIP",
      size: "8.5 MB",
      actionFormat: "package",
    },
  ];

  const handleDownload = (format: string) => {
    const url = getAssetDownloadUrl(missionId, format);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${missionId}_${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleRetryFailed = () => {
    setRetrying(true);
    setTimeout(() => {
      setRetrying(false);
      setFailedResolved(true);
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-[#080b10] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden text-zinc-100 flex flex-col max-h-[88vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-850 flex items-center justify-between bg-zinc-950/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <FolderDown className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                Export Center
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

        {/* Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 text-xs">
          {/* Section 1: READY */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>READY DELIVERABLES ({readyItems.length + (failedResolved ? 1 : 0)})</span>
              </span>
              <span className="text-[10px] font-mono text-zinc-500">Available for download</span>
            </div>

            <div className="space-y-2">
              {readyItems.map((item) => (
                <div
                  key={item.id}
                  className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between hover:border-zinc-700 transition-colors"
                >
                  <div className="space-y-0.5">
                    <div className="font-semibold text-white text-xs">{item.title}</div>
                    <div className="text-[11px] text-zinc-400 font-mono flex items-center gap-2">
                      <span className="text-emerald-400 font-bold">{item.type}</span>
                      <span>·</span>
                      <span>{item.size}</span>
                      <span>·</span>
                      <span className="text-zinc-500">Local & WGS84</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDownload(item.actionFormat)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-emerald-600 text-zinc-200 hover:text-white font-semibold text-xs transition-colors cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </button>
                </div>
              ))}

              {failedResolved && (
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-emerald-500/50 flex items-center justify-between transition-colors">
                  <div className="space-y-0.5">
                    <div className="font-semibold text-white text-xs">GIS Coordinate Package</div>
                    <div className="text-[11px] text-zinc-400 font-mono flex items-center gap-2">
                      <span className="text-emerald-400 font-bold">GeoPackage</span>
                      <span>·</span>
                      <span>1.8 MB</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownload("package")}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Section 2: PROCESSING */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase tracking-wider text-amber-400 font-bold flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                <span>PROCESSING QUEUE (1)</span>
              </span>
              <span className="text-[10px] font-mono text-zinc-500">82% completed</span>
            </div>

            <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="font-medium text-white">
                  Orthomosaic High-Resolution Resampling (0.5cm GSD)
                </span>
                <span className="font-mono text-emerald-400 font-bold">82%</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: "82%" }} />
              </div>
              <div className="text-[10px] font-mono text-zinc-500">
                Pyramidal GeoTIFF tile generation active · Est. remaining: 18s
              </div>
            </div>
          </div>

          {/* Section 3: FAILED */}
          {!failedResolved && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-red-400 font-bold flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>FAILED QUEUE (1)</span>
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-red-900/40 flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="font-semibold text-white text-xs">GIS Coordinate Reference Export</div>
                  <div className="text-[11px] text-red-400 font-mono">
                    Reason: missing EPSG coordinate reference header (defaulting to UTM Zone 32N)
                  </div>
                </div>

                <button
                  onClick={handleRetryFailed}
                  disabled={retrying}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold transition-colors cursor-pointer"
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${retrying ? "animate-spin" : ""}`} />
                  <span>{retrying ? "Retrying…" : "Retry"}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
