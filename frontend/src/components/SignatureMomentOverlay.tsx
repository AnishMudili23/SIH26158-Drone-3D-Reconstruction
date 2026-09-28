"use client";

import React from "react";
import { ArrowDown, Layers, Sparkles } from "lucide-react";

interface SignatureMomentOverlayProps {
  isOpen: boolean;
  onEnter: () => void;
  missionName?: string;
  structuresCount?: number;
  sceneArea?: string;
  coverage?: string;
}

export const SignatureMomentOverlay: React.FC<SignatureMomentOverlayProps> = ({
  isOpen,
  onEnter,
  missionName = "Zurich Infrastructure Survey",
  structuresCount = 3,
  sceneArea = "12,428 m²",
  coverage = "87%",
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#05070a] text-zinc-100 select-none animate-fadeIn">
      {/* Background ambient lighting */}
      <div className="absolute inset-0 bg-radial from-emerald-950/20 via-transparent to-transparent pointer-events-none" />

      <div className="text-center max-w-md px-6 space-y-8 z-10">
        <div className="space-y-2">
          <div className="text-xs uppercase tracking-widest font-mono text-emerald-400 font-bold">
            AEROMESH
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white uppercase">
            Your World is Ready
          </h1>
          <p className="text-xs text-zinc-500 font-mono">{missionName}</p>
        </div>

        {/* 3 Metric Pills */}
        <div className="grid grid-cols-3 gap-3 border-y border-zinc-800/80 py-5 font-mono">
          <div>
            <div className="text-lg font-bold text-white">{structuresCount}</div>
            <div className="text-[10px] text-zinc-500 uppercase mt-0.5">Structures</div>
          </div>
          <div>
            <div className="text-lg font-bold text-white">{sceneArea}</div>
            <div className="text-[10px] text-zinc-500 uppercase mt-0.5">Scene</div>
          </div>
          <div>
            <div className="text-lg font-bold text-emerald-400">{coverage}</div>
            <div className="text-[10px] text-zinc-500 uppercase mt-0.5">Coverage</div>
          </div>
        </div>

        {/* Enter Button */}
        <div>
          <button
            onClick={onEnter}
            className="w-full py-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm shadow-xl shadow-emerald-600/30 transition-all transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center justify-center gap-2"
          >
            <span>Enter 3D World</span>
            <ArrowDown className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
