"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight, X } from "lucide-react";

interface AeroMeshGuideProps {
  onReviewStructure?: () => void;
}

export const AeroMeshGuide: React.FC<AeroMeshGuideProps> = ({
  onReviewStructure,
}) => {
  const [isOpen, setIsOpen] = useState(true);

  if (!isOpen) return null;

  return (
    <div className="absolute bottom-6 right-6 z-30 max-w-xs rounded-xl border border-zinc-800 bg-[#090d13]/95 backdrop-blur-md p-4 shadow-2xl text-xs text-zinc-300 space-y-2 select-none">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 font-bold text-white uppercase text-[11px] font-mono">
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span>AeroMesh Guide</span>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-zinc-500 hover:text-white transition-colors cursor-pointer"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <p className="text-[11px] text-zinc-300 leading-relaxed">
        Your reconstruction is ready. I found <strong className="text-white">3 structures</strong> with sufficient multi-view evidence. The main structure has <strong className="text-emerald-400">85% confidence</strong>.
      </p>

      <div className="pt-1 flex items-center justify-between border-t border-zinc-800/80 text-[11px]">
        <span className="text-zinc-500 text-[10px]">Suggested next step</span>
        <button
          onClick={() => {
            onReviewStructure?.();
            setIsOpen(false);
          }}
          className="text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1 cursor-pointer transition-colors"
        >
          <span>Review Structure #1</span>
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};
