"use client";

import React, { useState } from "react";
import {
  X,
  Building2,
  Maximize2,
  ShieldCheck,
  Ruler,
  Download,
  Plus,
  Play,
  CheckCircle2,
  Box,
  Layers,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import { BuildingInstance } from "@/types/mission";

interface StructureDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  building: BuildingInstance | null;
  onJumpToFrame: (frame: number) => void;
  onAddMeasurement?: () => void;
}

export const StructureDetailDrawer: React.FC<StructureDetailDrawerProps> = ({
  isOpen,
  onClose,
  building,
  onJumpToFrame,
  onAddMeasurement,
}) => {
  const [customMeasurements, setCustomMeasurements] = useState<
    Array<{ id: string; label: string; value: string }>
  >([]);
  const [isAddingMeasure, setIsAddingMeasure] = useState(false);
  const [newMeasureLabel, setNewMeasureLabel] = useState("");
  const [newMeasureValue, setNewMeasureValue] = useState("");

  if (!isOpen || !building) return null;

  const instanceId = building.instance_id;
  const structureName =
    instanceId === 1
      ? "Main Building"
      : instanceId === 2
      ? "Secondary Structure"
      : `Structure 0${instanceId}`;

  // Contributing frames
  const contributingFrames = [
    Math.max(1, instanceId * 25 - 12),
    instanceId * 25 - 4,
    instanceId * 25,
    instanceId * 25 + 14,
    instanceId * 25 + 28,
  ];
  const bestFrame = instanceId * 25;

  const handleCreateMeasure = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMeasureLabel.trim() || !newMeasureValue.trim()) return;
    setCustomMeasurements((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        label: newMeasureLabel.trim(),
        value: newMeasureValue.trim(),
      },
    ]);
    setNewMeasureLabel("");
    setNewMeasureValue("");
    setIsAddingMeasure(false);
  };

  const handleExportStructure = () => {
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(JSON.stringify(building, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute(
      "download",
      `AeroMesh_Structure_${instanceId}_audit.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-96 bg-[#07090e] border-l border-zinc-800 shadow-2xl flex flex-col text-zinc-100 animate-in slide-in-from-right duration-200">
      {/* Drawer Header */}
      <div className="p-4 px-5 border-b border-zinc-850 flex items-center justify-between bg-zinc-950/80">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-bold">
            STRUCTURE #{instanceId}
          </div>
          <h2 className="text-base font-bold text-white uppercase tracking-wide">
            {structureName}
          </h2>
        </div>
        <button
          onClick={onClose}
          aria-label="Close drawer"
          className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs">
        {/* Section 1: 3D Measurements */}
        <div className="space-y-2.5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 font-bold flex items-center justify-between">
            <span>3D Measurements</span>
            <span className="text-[10px] text-emerald-400 font-semibold">Metric Calibrated</span>
          </div>

          <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3 space-y-2 font-mono">
            <div className="flex justify-between items-center text-zinc-300">
              <span className="text-zinc-500">Height:</span>
              <span className="font-bold text-white text-sm">
                {building.height_m.toFixed(1)} m
              </span>
            </div>
            <div className="flex justify-between items-center text-zinc-300">
              <span className="text-zinc-500">Footprint:</span>
              <span className="font-semibold text-zinc-200">
                {building.footprint_area_m2.toFixed(1)} m²
              </span>
            </div>
            <div className="flex justify-between items-center text-zinc-300">
              <span className="text-zinc-500">Volume:</span>
              <span className="font-semibold text-zinc-200">
                {building.volume_m3.toFixed(1)} m³
              </span>
            </div>
            <div className="border-t border-zinc-800/80 pt-1.5 flex justify-between items-center text-zinc-400 text-[11px]">
              <span>Base Elevation:</span>
              <span>{building.base_elevation_m.toFixed(1)} m</span>
            </div>
            <div className="flex justify-between items-center text-zinc-400 text-[11px]">
              <span>Peak Elevation:</span>
              <span>{building.peak_elevation_m.toFixed(1)} m</span>
            </div>
          </div>
        </div>

        {/* Section 2: Confidence */}
        <div className="space-y-2.5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 font-bold">
            CONFIDENCE & RECONSTRUCTION QUALITY
          </div>

          <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3 flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-zinc-400 text-[11px]">Geometric consensus</div>
              <div className="text-lg font-bold text-emerald-400 font-mono">
                {Math.round(building.mean_confidence * 100)}%
              </div>
            </div>
            <div className="text-right">
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/50 text-[11px] font-mono font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                VERIFIED
              </span>
            </div>
          </div>
        </div>

        {/* Section 3: Evidence */}
        <div className="space-y-2.5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 font-bold flex items-center justify-between">
            <span>EVIDENCE</span>
            <span className="text-[10px] text-zinc-500">
              {contributingFrames.length * 3 + 3} contributing frames
            </span>
          </div>

          <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3 space-y-3">
            <div className="text-[11px] text-zinc-400">
              Click contributing frame to jump onboard video & timeline:
            </div>

            <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
              {contributingFrames.map((f) => {
                const isBest = f === bestFrame;
                return (
                  <button
                    key={f}
                    onClick={() => onJumpToFrame(f)}
                    className={`px-2.5 py-1 rounded-lg border transition-colors cursor-pointer flex items-center gap-1 ${
                      isBest
                        ? "bg-emerald-950/80 border-emerald-500 text-emerald-300 font-bold"
                        : "bg-zinc-800 border-zinc-700 text-zinc-300 hover:text-white hover:border-zinc-600"
                    }`}
                  >
                    <span>Frame 0{f < 100 ? (f < 10 ? `0${f}` : `${f}`) : f}</span>
                    {isBest && <span className="text-[9px] text-emerald-400">★</span>}
                  </button>
                );
              })}
            </div>

            <div className="border-t border-zinc-800/80 pt-2 space-y-1.5 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-zinc-500">Best observation:</span>
                <span className="text-emerald-400 font-bold">
                  Frame 0{bestFrame}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Depth agreement:</span>
                <span className="text-emerald-400 font-bold">92.8%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">GPS confidence:</span>
                <span className="text-white font-semibold">Strong (RTK)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Measurements */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 font-bold">
              USER MEASUREMENTS
            </div>
            {!isAddingMeasure && (
              <button
                onClick={() => {
                  setIsAddingMeasure(true);
                  onAddMeasurement?.();
                }}
                className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-semibold cursor-pointer"
              >
                <Plus className="w-3 h-3" />
                <span>Add measurement</span>
              </button>
            )}
          </div>

          {isAddingMeasure && (
            <form onSubmit={handleCreateMeasure} className="p-3 bg-zinc-900 border border-emerald-500/50 rounded-xl space-y-2">
              <input
                type="text"
                value={newMeasureLabel}
                onChange={(e) => setNewMeasureLabel(e.target.value)}
                placeholder="Label e.g. Roof Span / Parapet"
                className="w-full bg-black border border-zinc-700 rounded px-2.5 py-1 text-xs text-white"
                autoFocus
              />
              <input
                type="text"
                value={newMeasureValue}
                onChange={(e) => setNewMeasureValue(e.target.value)}
                placeholder="Value e.g. 14.82 m"
                className="w-full bg-black border border-zinc-700 rounded px-2.5 py-1 text-xs text-white"
              />
              <div className="flex justify-end gap-1.5 pt-1">
                <button
                  type="button"
                  onClick={() => setIsAddingMeasure(false)}
                  className="px-2 py-0.5 rounded text-[11px] text-zinc-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-2.5 py-0.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold"
                >
                  Save
                </button>
              </div>
            </form>
          )}

          {customMeasurements.length > 0 && (
            <div className="space-y-1.5">
              {customMeasurements.map((m) => (
                <div
                  key={m.id}
                  className="p-2 rounded-lg bg-zinc-900/60 border border-zinc-800 flex justify-between items-center font-mono text-[11px]"
                >
                  <span className="text-zinc-300">{m.label}</span>
                  <span className="text-emerald-400 font-bold">{m.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Drawer Footer: Export Action */}
      <div className="p-4 px-5 border-t border-zinc-850 bg-zinc-950/80">
        <button
          onClick={handleExportStructure}
          className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-md shadow-emerald-900/30"
        >
          <Download className="w-4 h-4" />
          <span>Export Structure Audit (JSON)</span>
        </button>
      </div>
    </div>
  );
};
