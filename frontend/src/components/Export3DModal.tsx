"use client";

import React, { useState } from "react";
import {
  X,
  Download,
  Box,
  Layers,
  Compass,
  CheckCircle2,
  FileCode,
  Sparkles,
} from "lucide-react";
import { getAssetDownloadUrl } from "@/lib/api";

interface Export3DModalProps {
  isOpen: boolean;
  onClose: () => void;
  missionId: string;
  missionName?: string;
}

export const Export3DModal: React.FC<Export3DModalProps> = ({
  isOpen,
  onClose,
  missionId,
  missionName = "Zurich Infrastructure Survey",
}) => {
  const [selectedFormat, setSelectedFormat] = useState<"glb" | "ply" | "obj" | "las">("glb");
  const [selectedCoordSystem, setSelectedCoordSystem] = useState<
    "local" | "wgs84" | "project"
  >("local");
  const [isExporting, setIsExporting] = useState(false);

  if (!isOpen) return null;

  const handleExport = () => {
    setIsExporting(true);
    const downloadUrl = getAssetDownloadUrl(missionId, selectedFormat);

    // Trigger browser download via anchor
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `${missionId}_${selectedFormat}.${selectedFormat === "glb" ? "glb" : selectedFormat === "ply" ? "ply" : selectedFormat === "obj" ? "obj" : "las"}`;
    document.body.appendChild(link);
    link.click();
    link.remove();

    setTimeout(() => {
      setIsExporting(false);
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-md bg-[#080b10] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden text-zinc-100 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-850 flex items-center justify-between bg-zinc-950/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Box className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                Export 3D Model
              </h2>
              <p className="text-[11px] text-zinc-400 font-mono truncate max-w-[240px]">
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
        <div className="p-6 space-y-6 text-xs">
          {/* Format Selection */}
          <div className="space-y-2">
            <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 font-bold">
              Format
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: "glb", label: "GLB", desc: "Binary glTF (Web & Unreal)" },
                { id: "ply", label: "PLY", desc: "Polygon File Format" },
                { id: "obj", label: "OBJ", desc: "Wavefront with Material" },
                { id: "las", label: "LAS", desc: "ASPRS Point Cloud" },
              ].map((fmt) => (
                <button
                  key={fmt.id}
                  type="button"
                  onClick={() => setSelectedFormat(fmt.id as any)}
                  className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                    selectedFormat === fmt.id
                      ? "bg-emerald-950/30 border-emerald-500 text-white shadow-sm ring-1 ring-emerald-500/50"
                      : "bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <div className="font-bold font-mono text-sm text-white">{fmt.label}</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">{fmt.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Coordinate System Selection */}
          <div className="space-y-2">
            <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 font-bold">
              Coordinate System
            </label>
            <div className="space-y-2">
              {[
                { id: "local", label: "Local Metric", desc: "Origin at flight takeoff point (meters)" },
                { id: "wgs84", label: "WGS84 / GPS", desc: "Latitude, longitude, ellipsoidal height" },
                { id: "project", label: "Project Coordinates", desc: "UTM / Swiss LV95 projected grid" },
              ].map((coord) => (
                <label
                  key={coord.id}
                  onClick={() => setSelectedCoordSystem(coord.id as any)}
                  className={`flex items-center justify-between p-2.5 rounded-xl border cursor-pointer transition-colors ${
                    selectedCoordSystem === coord.id
                      ? "bg-emerald-950/20 border-emerald-500/60 text-white"
                      : "bg-zinc-900/30 border-zinc-800/80 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <input
                      type="radio"
                      name="coord"
                      checked={selectedCoordSystem === coord.id}
                      onChange={() => setSelectedCoordSystem(coord.id as any)}
                      className="accent-emerald-500"
                    />
                    <span className="font-medium text-white">{coord.label}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500 font-mono">{coord.desc}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-zinc-850 bg-zinc-950/80 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/25 transition-all cursor-pointer disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{isExporting ? "Downloading…" : `Export ${selectedFormat.toUpperCase()}`}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
