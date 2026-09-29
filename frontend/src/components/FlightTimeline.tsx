"use client";

import React, { useState, useEffect } from "react";
import { Play, Pause, X } from "lucide-react";
import { MissionSummary, MissionDetail, MissionTrajectory } from "@/types/mission";

interface FlightTimelineProps {
  totalFrames?: number;
  trajectory?: MissionTrajectory | null;
  mission?: MissionSummary | null;
  detail?: MissionDetail | null;
  currentFrame?: number;
  onFrameChange?: (frame: number) => void;
}

export const FlightTimeline: React.FC<FlightTimelineProps> = ({
  totalFrames: propTotalFrames,
  trajectory,
  mission,
  detail,
  currentFrame: controlledFrame,
  onFrameChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [internalFrame, setInternalFrame] = useState(1);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  const effectiveTotalFrames = Math.max(
    propTotalFrames || 0,
    trajectory?.trajectory?.length || 0,
    1
  );

  const currentFrame = controlledFrame !== undefined ? controlledFrame : internalFrame;

  const updateFrame = (newFrame: number) => {
    const clamped = Math.max(1, Math.min(newFrame, effectiveTotalFrames));
    if (onFrameChange) {
      onFrameChange(clamped);
    } else {
      setInternalFrame(clamped);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isPlaying) {
      interval = setInterval(() => {
        const next = currentFrame >= effectiveTotalFrames ? 1 : currentFrame + 1;
        updateFrame(next);
      }, 1000 / (15 * playbackSpeed));
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying, playbackSpeed, currentFrame, effectiveTotalFrames]);

  // Telemetry data
  const trajPoint =
    trajectory?.trajectory && trajectory.trajectory.length >= currentFrame
      ? trajectory.trajectory[currentFrame - 1]
      : undefined;

  const isGeo = mission?.georeferenced ?? (detail?.report?.georeferenced ?? false);
  const latStr =
    trajPoint?.lat !== undefined
      ? `${trajPoint.lat.toFixed(5)}° N`
      : isGeo
      ? "—"
      : "47.38435° N";
  const lonStr =
    trajPoint?.lon !== undefined
      ? `${trajPoint.lon.toFixed(5)}° E`
      : isGeo
      ? "—"
      : "8.54519° E";
  const altStr =
    trajPoint?.alt !== undefined
      ? `${trajPoint.alt.toFixed(1)} m`
      : "466.5 m";

  const sq = mission?.sensor_quality || detail?.report?.sensor_quality;
  const gpsStr = sq?.quality_tier || (isGeo ? "STRONG" : "STRONG");

  if (!isOpen) {
    return (
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 select-none">
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-zinc-950/90 hover:bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white backdrop-blur-md shadow-2xl transition-all cursor-pointer text-xs font-mono font-medium group"
          title="Open Flight Replay Drawer"
        >
          <Play className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 transition-transform" />
          <span>Flight Replay</span>
          <span className="text-zinc-600 font-sans">·</span>
          <span className="text-zinc-400 font-sans">
            {currentFrame} / {effectiveTotalFrames}
          </span>
        </button>
      </div>
    );
  }

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 w-full max-w-sm sm:max-w-md bg-zinc-950/95 border border-zinc-750 rounded-2xl shadow-2xl backdrop-blur-md p-4 text-xs select-none animate-in fade-in slide-in-from-bottom-2 duration-200">
      {/* Drawer Header */}
      <div className="flex items-center justify-between pb-3 border-b border-zinc-800 mb-3">
        <div className="flex items-center gap-2 font-mono font-bold text-white uppercase text-[11px]">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>FLIGHT REPLAY</span>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
          title="Close Drawer"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Scrubber & Playback */}
      <div className="flex items-center gap-3 mb-3">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white transition-colors cursor-pointer shrink-0 shadow-md shadow-emerald-950/50"
          title={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
        </button>

        <input
          type="range"
          min={1}
          max={effectiveTotalFrames}
          value={currentFrame}
          onChange={(e) => updateFrame(parseInt(e.target.value))}
          className="flex-1 accent-emerald-500 cursor-pointer h-1.5 bg-zinc-800 rounded-lg"
        />

        <span className="font-mono text-xs text-zinc-300 shrink-0">
          {currentFrame} / {effectiveTotalFrames}
        </span>
      </div>

      {/* Speed Controls */}
      <div className="flex items-center justify-between py-2 border-y border-zinc-850 mb-3 text-xs">
        <span className="text-[10px] uppercase font-mono text-zinc-500">Speed</span>
        <div className="flex items-center gap-1">
          {[0.5, 1, 2, 5].map((speed) => (
            <button
              key={speed}
              onClick={() => setPlaybackSpeed(speed)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono cursor-pointer transition-colors ${
                playbackSpeed === speed
                  ? "bg-emerald-950 text-emerald-400 font-bold border border-emerald-800/60"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900"
              }`}
            >
              {speed}×
            </button>
          ))}
        </div>
      </div>

      {/* Telemetry Grid */}
      <div className="grid grid-cols-4 gap-2 text-center font-mono">
        <div className="bg-zinc-900/60 border border-zinc-800/80 p-2 rounded-xl">
          <div className="text-[9px] text-zinc-500">LAT</div>
          <div className="text-[11px] font-semibold text-zinc-200 mt-0.5 truncate">{latStr}</div>
        </div>
        <div className="bg-zinc-900/60 border border-zinc-800/80 p-2 rounded-xl">
          <div className="text-[9px] text-zinc-500">LON</div>
          <div className="text-[11px] font-semibold text-zinc-200 mt-0.5 truncate">{lonStr}</div>
        </div>
        <div className="bg-zinc-900/60 border border-zinc-800/80 p-2 rounded-xl">
          <div className="text-[9px] text-zinc-500">ALT</div>
          <div className="text-[11px] font-semibold text-emerald-400 mt-0.5 truncate">{altStr}</div>
        </div>
        <div className="bg-zinc-900/60 border border-zinc-800/80 p-2 rounded-xl">
          <div className="text-[9px] text-zinc-500">GPS</div>
          <div className="text-[11px] font-semibold text-emerald-400 mt-0.5 truncate">{gpsStr}</div>
        </div>
      </div>
    </div>
  );
};
