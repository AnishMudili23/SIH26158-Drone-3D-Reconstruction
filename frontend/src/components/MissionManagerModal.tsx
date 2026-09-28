"use client";

import React, { useState } from "react";
import {
  X,
  Search,
  Plus,
  Trash2,
  Edit2,
  Copy,
  Archive,
  ArrowRight,
  ShieldCheck,
  FolderOpen,
  Sparkles,
  AlertTriangle,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { MissionSummary } from "@/types/mission";
import { deleteMission, clearDemoMissions, renameMission, archiveMission } from "@/lib/api";

interface MissionManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  missions: MissionSummary[];
  selectedMissionId: string;
  onSelectMission: (missionId: string) => void;
  onNewMission: () => void;
  onRefresh: () => void;
}

export const MissionManagerModal: React.FC<MissionManagerModalProps> = ({
  isOpen,
  onClose,
  missions,
  selectedMissionId,
  onSelectMission,
  onNewMission,
  onRefresh,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"all" | "my" | "demo">("all");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 4;

  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);

  if (!isOpen) return null;

  const filteredMissions = missions.filter((m) =>
    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const myMissions = filteredMissions.filter(
    (m) => m.category === "MY_MISSIONS" || (!m.is_demo && m.id !== "zurich_mav_mission")
  );
  const demoMissions = filteredMissions.filter(
    (m) => m.category === "DEMO_MISSIONS" || m.is_demo || m.id === "zurich_mav_mission"
  );

  const displayedList =
    activeTab === "my"
      ? myMissions
      : activeTab === "demo"
      ? demoMissions
      : filteredMissions;

  const totalPages = Math.max(1, Math.ceil(displayedList.length / pageSize));
  const pageClamped = Math.min(currentPage, totalPages);
  const pagedItems = displayedList.slice((pageClamped - 1) * pageSize, pageClamped * pageSize);

  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    setCurrentPage(1);
  };

  const handleTabChange = (tab: "all" | "my" | "demo") => {
    setActiveTab(tab);
    setCurrentPage(1);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Permanently delete mission "${name}"? This cannot be undone.`)) {
      return;
    }
    try {
      setIsActionLoading(true);
      await deleteMission(id);
      onRefresh();
    } catch (e) {
      alert(`Could not delete mission: ${e}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleStartRename = (id: string, currentName: string) => {
    setRenamingId(id);
    setRenameValue(currentName);
  };

  const handleSaveRename = async (id: string) => {
    if (!renameValue.trim()) return;
    try {
      setIsActionLoading(true);
      await renameMission(id, renameValue.trim());
      setRenamingId(null);
      onRefresh();
    } catch (e) {
      alert(`Could not rename mission: ${e}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleArchive = async (id: string) => {
    try {
      setIsActionLoading(true);
      await archiveMission(id);
      onRefresh();
    } catch (e) {
      alert(`Could not archive mission: ${e}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleClearDemoData = async () => {
    try {
      setIsActionLoading(true);
      await clearDemoMissions();
      setShowClearConfirm(false);
      onRefresh();
    } catch (e) {
      alert(`Could not clear demo data: ${e}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-3xl bg-[#080b10] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden text-zinc-100 flex flex-col max-h-[88vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-zinc-850 flex items-center justify-between bg-zinc-950/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <FolderOpen className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                Missions Management
              </h2>
              <p className="text-[11px] text-zinc-400">
                Organize, open, inspect, or archive operational flight surveys
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                onClose();
                onNewMission();
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>+ New Mission</span>
            </button>

            <button
              onClick={onClose}
              aria-label="Close modal"
              className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search Bar & Category Filter Tabs */}
        <div className="p-4 px-6 border-b border-zinc-850/80 bg-zinc-950/30 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search missions by name or ID…"
              className="w-full pl-9 pr-4 py-2 bg-zinc-900 border border-zinc-800 rounded-xl text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 font-sans"
            />
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 p-0.5 rounded-xl text-xs font-mono shrink-0">
            <button
              onClick={() => handleTabChange("all")}
              className={`px-3 py-1 rounded-lg transition-colors cursor-pointer ${
                activeTab === "all"
                  ? "bg-zinc-800 text-white font-bold"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              All ({filteredMissions.length})
            </button>
            <button
              onClick={() => handleTabChange("my")}
              className={`px-3 py-1 rounded-lg transition-colors cursor-pointer ${
                activeTab === "my"
                  ? "bg-zinc-800 text-white font-bold"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              My ({myMissions.length})
            </button>
            <button
              onClick={() => handleTabChange("demo")}
              className={`px-3 py-1 rounded-lg transition-colors cursor-pointer flex items-center gap-1 ${
                activeTab === "demo"
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800/50 font-bold"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Sparkles className="w-3 h-3 text-emerald-400" />
              <span>Demo ({demoMissions.length})</span>
            </button>
          </div>

          <div className="hidden md:flex items-center gap-2 text-xs font-mono text-zinc-400 shrink-0">
            <button
              onClick={() => setShowClearConfirm(true)}
              className="text-[11px] text-zinc-500 hover:text-red-400 underline transition-colors cursor-pointer"
            >
              Clear Demo Data
            </button>
          </div>
        </div>

        {/* Clear Confirmation Sub-banner */}
        {showClearConfirm && (
          <div className="p-3 px-6 bg-red-950/40 border-b border-red-900/50 flex items-center justify-between text-xs text-red-200">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>Remove all demonstration and scratch missions? Real missions will not be affected.</span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-[11px] cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleClearDemoData}
                disabled={isActionLoading}
                className="px-2.5 py-1 rounded bg-red-600 hover:bg-red-500 text-white font-semibold text-[11px] cursor-pointer"
              >
                Confirm Clear
              </button>
            </div>
          </div>
        )}

        {/* Scrollable Mission Lists */}
        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          {pagedItems.length === 0 ? (
            <div className="p-10 rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/30 text-center space-y-3">
              <div className="text-zinc-400 text-xs">
                {searchQuery
                  ? `No missions match "${searchQuery}".`
                  : activeTab === "my"
                  ? "No custom user missions found yet."
                  : "No missions available."}
              </div>
              <button
                onClick={() => {
                  onClose();
                  onNewMission();
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Create New Mission</span>
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              {pagedItems.map((m) => renderMissionCard(m))}
            </div>
          )}
        </div>

        {/* Pager Footer Navigation */}
        <div className="p-4 px-6 border-t border-zinc-850 bg-zinc-950/80 flex items-center justify-between text-xs font-mono text-zinc-400">
          <span className="text-[11px] text-zinc-500">
            {displayedList.length === 0
              ? "0 missions"
              : `Showing ${(pageClamped - 1) * pageSize + 1}–${Math.min(
                  pageClamped * pageSize,
                  displayedList.length
                )} of ${displayedList.length} missions`}
          </span>

          {totalPages > 1 && (
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={pageClamped <= 1}
                className="px-2.5 py-1 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-40 disabled:hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors cursor-pointer disabled:cursor-not-allowed"
              >
                ← Prev
              </button>

              <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((num) => (
                  <button
                    key={num}
                    onClick={() => setCurrentPage(num)}
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
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={pageClamped >= totalPages}
                className="px-2.5 py-1 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-40 disabled:hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors cursor-pointer disabled:cursor-not-allowed"
              >
                Next →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  function renderMissionCard(m: MissionSummary) {
    const isSelected = m.id === selectedMissionId;
    const isRenaming = renamingId === m.id;

    return (
      <div
        key={m.id}
        className={`p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          isSelected
            ? "bg-zinc-900/90 border-emerald-500 shadow-sm ring-1 ring-emerald-500/40"
            : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-700"
        }`}
      >
        <div className="space-y-1.5 min-w-0 flex-1">
          {/* Title & Status */}
          <div className="flex items-center gap-2 flex-wrap">
            {isRenaming ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  className="bg-black border border-emerald-500 rounded px-2 py-0.5 text-xs text-white"
                  autoFocus
                />
                <button
                  onClick={() => handleSaveRename(m.id)}
                  className="px-2 py-0.5 rounded bg-emerald-600 text-white text-[10px] font-semibold"
                >
                  Save
                </button>
                <button
                  onClick={() => setRenamingId(null)}
                  className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 text-[10px]"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <>
                <span className="font-semibold text-white text-sm truncate">{m.name}</span>
                {m.is_demo && (
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 border border-zinc-750">
                    SIMULATED
                  </span>
                )}
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40 font-semibold">
                  ● {m.status || "READY"}
                </span>
              </>
            )}
          </div>

          {/* Subtitle metrics */}
          <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono flex-wrap">
            <span>{m.mission_type || "Building"}</span>
            <span>·</span>
            <span>{m.total_frames || 350} frames</span>
            <span>·</span>
            <span>{m.sparse_points ? `${(m.sparse_points / 1000).toFixed(0)}K points` : "32K points"}</span>
            <span>·</span>
            <span>{m.building_count || 3} structures</span>
          </div>
        </div>

        {/* Actions row */}
        <div className="flex items-center gap-2 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-zinc-800">
          <button
            onClick={() => {
              onSelectMission(m.id);
              onClose();
            }}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors cursor-pointer"
          >
            <span>Open</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>

          {!m.is_demo && m.id !== "zurich_mav_mission" && (
            <>
              <button
                onClick={() => handleStartRename(m.id, m.name)}
                title="Rename mission"
                className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white transition-colors cursor-pointer"
              >
                <Edit2 className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => handleArchive(m.id)}
                title="Archive mission"
                className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white transition-colors cursor-pointer"
              >
                <Archive className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => handleDelete(m.id, m.name)}
                title="Delete mission"
                className="p-1.5 rounded-lg bg-zinc-800 hover:bg-red-950 text-zinc-400 hover:text-red-400 transition-colors cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </>
          )}
        </div>
      </div>
    );
  }
};
