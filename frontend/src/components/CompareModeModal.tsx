"use client";

import React, { useState } from "react";
import { X, Columns, ArrowRight, CheckCircle2, AlertTriangle, Layers } from "lucide-react";

interface CompareModeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CompareModeModal: React.FC<CompareModeModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [sliderPos, setSliderPos] = useState(50);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#090d13] border border-zinc-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden text-zinc-100 flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Columns className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-white">
              Multi-Temporal Site Comparison
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Comparison Body */}
        <div className="p-6 space-y-5 text-xs">
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="text-zinc-300">
              <span className="text-zinc-500">Flight A (Baseline):</span> Zurich Flight #01 (14 Sep)
            </div>
            <div className="text-emerald-400 font-semibold">
              <span className="text-zinc-500">Flight B (Re-survey):</span> Zurich Flight #02 (28 Sep)
            </div>
          </div>

          {/* Interactive Comparison Split Viewer Simulation */}
          <div className="relative h-64 rounded-xl border border-zinc-800 bg-[#05070a] overflow-hidden">
            {/* Left side (Flight A - Pre-construction) */}
            <div
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-zinc-900 to-zinc-950 flex items-center justify-center border-r border-emerald-500"
              style={{ width: `${sliderPos}%` }}
            >
              <div className="text-center p-4">
                <div className="text-[10px] font-mono text-zinc-500 uppercase">Baseline Geometry</div>
                <div className="text-sm font-bold text-white mt-1">Ground Elevation: 412.0 m</div>
                <div className="text-[11px] text-zinc-400 mt-1">1 Structure detected</div>
              </div>
            </div>

            {/* Right side (Flight B - Post-construction) */}
            <div
              className="absolute inset-y-0 right-0 bg-[#060a0f] flex items-center justify-center"
              style={{ width: `${100 - sliderPos}%` }}
            >
              <div className="text-center p-4">
                <div className="text-[10px] font-mono text-emerald-400 uppercase">Re-survey Geometry</div>
                <div className="text-sm font-bold text-white mt-1">New Structure: +11.8 m Height</div>
                <div className="text-[11px] text-emerald-300 mt-1">3 Structures (+2 New)</div>
              </div>
            </div>

            {/* Draggable Divider */}
            <div
              className="absolute top-0 bottom-0 w-1 bg-emerald-400 cursor-ew-resize z-20 flex items-center justify-center shadow-lg"
              style={{ left: `${sliderPos}%` }}
            >
              <div className="w-5 h-5 rounded-full bg-emerald-500 text-black flex items-center justify-center text-[10px] font-bold shadow-md">
                ↔
              </div>
            </div>

            {/* Range Slider for Interaction */}
            <input
              type="range"
              min="10"
              max="90"
              value={sliderPos}
              onChange={(e) => setSliderPos(Number(e.target.value))}
              className="absolute inset-x-0 bottom-3 mx-4 opacity-30 hover:opacity-100 transition-opacity cursor-ew-resize accent-emerald-500"
            />
          </div>

          {/* Differential Change Findings */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 font-mono">Structural Change</div>
              <div className="text-xs font-bold text-emerald-400 mt-0.5">+2 New Built Prisms</div>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 font-mono">Volume Variance</div>
              <div className="text-xs font-bold text-white mt-0.5">+1,447.7 m³ Mass</div>
            </div>
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
              <div className="text-[10px] text-zinc-500 font-mono">Ground Settlement</div>
              <div className="text-xs font-bold text-white mt-0.5">&lt; 0.02 m (Stable)</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
