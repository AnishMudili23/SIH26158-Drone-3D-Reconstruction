"use client";

import React, { useState, useEffect } from "react";
import { Play, Pause, RotateCcw } from "lucide-react";
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

  const progressPct = ((currentFrame / effectiveTotalFrames) * 100);
  const timeSeconds = ((currentFrame - 1) / 15).toFixed(1);

  // Dynamic telemetry from the current trajectory frame
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
      : "N/A (LOCAL)";
  const lonStr =
    trajPoint?.lon !== undefined
      ? `${trajPoint.lon.toFixed(5)}° E`
      : isGeo
      ? "—"
      : "N/A (LOCAL)";
  const altStr =
    trajPoint?.alt !== undefined
      ? `${trajPoint.alt.toFixed(1)}m`
      : "—";

  const sq = mission?.sensor_quality || detail?.report?.sensor_quality;
  const gpsStr = sq?.quality_tier || (isGeo ? "STRONG" : "NONE");
  const imuStr = sq?.has_imu ? "ACTIVE" : "N/A";
  const modeStr = sq?.recommended_mode || (isGeo ? "STRONG_GPS" : "LOCAL_METRIC");

  const confPct =
    detail?.report?.high_confidence_points_pct ??
    (detail?.report?.semantic_quality?.mean_semantic_confidence
      ? detail.report.semantic_quality.mean_semantic_confidence * 100
      : undefined);
  const confStr = confPct !== undefined ? `${confPct.toFixed(0)}%` : "—";

  return (
    <footer className="h-16 border-t border-zinc-800 bg-zinc-950/95 px-6 flex items-center justify-between z-20 shrink-0 select-none text-xs">
      {/* Playback Controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="w-8 h-8 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center transition-colors shadow"
          title={isPlaying ? "Pause" : "Play"}
          aria-label={isPlaying ? "Pause playback" : "Play playback"}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>

        <button
          onClick={() => {
            updateFrame(1);
            setIsPlaying(false);
          }}
          className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Restart Flight"
          aria-label="Restart flight"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        {/* Frame Paging Step Buttons */}
        <div className="flex items-center gap-1 font-mono text-[10px]">
          <button
            onClick={() => updateFrame(currentFrame - 25)}
            className="px-1.5 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-800 transition-colors cursor-pointer"
            title="Jump back 25 frames (keyframe hop)"
          >
            -25
          </button>
          <button
            onClick={() => updateFrame(currentFrame - 1)}
            className="px-1.5 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-800 transition-colors cursor-pointer"
            title="Step back 1 frame"
          >
            -1
          </button>
          <button
            onClick={() => updateFrame(currentFrame + 1)}
            className="px-1.5 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-800 transition-colors cursor-pointer"
            title="Step forward 1 frame"
          >
            +1
          </button>
          <button
            onClick={() => updateFrame(currentFrame + 25)}
            className="px-1.5 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-800 transition-colors cursor-pointer"
            title="Jump forward 25 frames (keyframe hop)"
          >
            +25
          </button>
        </div>

        {/* Speed toggle */}
        <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded p-0.5 text-[10px] font-mono">
          {[1, 2, 5].map((speed) => (
            <button
              key={speed}
              onClick={() => setPlaybackSpeed(speed)}
              className={`px-1.5 py-0.5 rounded transition-colors ${
                playbackSpeed === speed
                  ? "bg-zinc-700 text-white font-bold"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>

      {/* Scrubber & Timeline Progress */}
      <div className="flex-1 max-w-xl mx-6 space-y-1">
        <div className="flex justify-between text-[10px] text-zinc-400 font-mono">
          <span>Flight Replay: {timeSeconds}s</span>
          <span>
            Frame {currentFrame} / {effectiveTotalFrames} ({progressPct.toFixed(0)}%)
          </span>
        </div>

        <input
          type="range"
          min="1"
          max={effectiveTotalFrames}
          value={currentFrame}
          onChange={(e) => updateFrame(parseInt(e.target.value, 10))}
          aria-label="Flight timeline frame scrubber"
          className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
      </div>

      {/* Telemetry Stream Readouts (Frame-accurate dynamic telemetry) */}
      <div className="hidden lg:flex items-center gap-4 text-[11px] font-mono text-zinc-400 border-l border-zinc-800 pl-4 shrink-0">
        <div>
          <span className="text-zinc-500">LAT:</span> {latStr}
        </div>
        <div>
          <span className="text-zinc-500">LON:</span> {lonStr}
        </div>
        <div>
          <span className="text-zinc-500">ALT:</span> {altStr}
        </div>
        <div>
          <span className="text-zinc-500">GPS:</span>{" "}
          <span className={gpsStr === "NONE" || gpsStr === "LOCAL_METRIC" ? "text-amber-400" : "text-emerald-400"}>
            {gpsStr}
          </span>
        </div>
        <div>
          <span className="text-zinc-500">IMU:</span>{" "}
          <span className={imuStr === "ACTIVE" ? "text-emerald-400" : "text-zinc-500"}>
            {imuStr}
          </span>
        </div>
        <div>
          <span className="text-zinc-500">CONF:</span>{" "}
          <span className="text-emerald-400 font-semibold">{confStr}</span>
        </div>
        <div className="text-emerald-400 font-semibold">
          <span className="text-zinc-500">MODE:</span> {modeStr}
        </div>
      </div>
    </footer>
  );
};
