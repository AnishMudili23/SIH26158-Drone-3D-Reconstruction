"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  MoreHorizontal,
  Info,
  Edit2,
  Copy,
  Archive,
  Trash2,
} from "lucide-react";
import { MissionSummary, MissionDetail } from "@/types/mission";

interface PipelineWorkflowBarProps {
  mission?: MissionSummary;
  detail?: MissionDetail | null;
  onOpenOverview?: () => void;
  onRename?: () => void;
  onDuplicate?: () => void;
  onArchive?: () => void;
  onDelete?: () => void;
  // Optional backward compatibility
  onOpenEvidence?: () => void;
  onOpenMeasurements?: () => void;
  onOpenExports?: () => void;
}

export const PipelineWorkflowBar: React.FC<PipelineWorkflowBarProps> = ({
  mission,
  detail,
  onOpenOverview,
  onRename,
  onDuplicate,
  onArchive,
  onDelete,
}) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    if (isMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isMenuOpen]);

  const missionName = mission?.name || "Zurich Infrastructure";
  const missionType = mission?.mission_type || "Building Inspection";

  return (
    <div className="border-b border-zinc-850 bg-[#06080d] px-6 py-2.5 flex items-center justify-between select-none">
      {/* Left: Mission Identity & Type */}
      <div
        onClick={onOpenOverview}
        className="group cursor-pointer flex flex-col"
        title="Click to view mission details"
      >
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-bold uppercase tracking-wider text-white font-mono group-hover:text-emerald-400 transition-colors">
            {missionName}
          </h1>
          <span className="opacity-0 group-hover:opacity-100 transition-opacity text-zinc-500">
            <Info className="w-3.5 h-3.5" />
          </span>
        </div>
        <span className="text-[11px] text-zinc-400 font-sans capitalize">
          {missionType.toLowerCase()}
        </span>
      </div>

      {/* Right: Status badge & Actions dropdown ⋯ */}
      <div className="flex items-center gap-3">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Ready
        </span>

        {/* ⋯ Contextual Actions Dropdown */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="p-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white transition-colors cursor-pointer"
            title="Mission actions"
            aria-label="Mission actions menu"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {isMenuOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 rounded-xl bg-zinc-950 border border-zinc-800 shadow-2xl p-1 z-50 text-xs">
              <button
                onClick={() => {
                  setIsMenuOpen(false);
                  onOpenOverview?.();
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-900 transition-colors text-left cursor-pointer"
              >
                <Info className="w-3.5 h-3.5 text-emerald-400" />
                <span>Mission details</span>
              </button>
              {onRename && (
                <button
                  onClick={() => {
                    setIsMenuOpen(false);
                    onRename();
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-900 transition-colors text-left cursor-pointer"
                >
                  <Edit2 className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Rename</span>
                </button>
              )}
              {onDuplicate && (
                <button
                  onClick={() => {
                    setIsMenuOpen(false);
                    onDuplicate();
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-900 transition-colors text-left cursor-pointer"
                >
                  <Copy className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Duplicate</span>
                </button>
              )}
              {onArchive && (
                <button
                  onClick={() => {
                    setIsMenuOpen(false);
                    onArchive();
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-900 transition-colors text-left cursor-pointer"
                >
                  <Archive className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Archive</span>
                </button>
              )}
              {onDelete && (
                <>
                  <div className="h-px bg-zinc-850 my-1" />
                  <button
                    onClick={() => {
                      setIsMenuOpen(false);
                      onDelete();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-950/30 transition-colors text-left cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete</span>
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
