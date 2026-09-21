"use client";

import React, { useState, useEffect } from "react";
import { Play, Pause, RotateCcw, FastForward } from "lucide-react";

interface FlightTimelineProps {
  totalFrames?: number;
}

export const FlightTimeline: React.FC<FlightTimelineProps> = ({
  totalFrames = 350,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrame, setCurrentFrame] = useState(1);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentFrame((prev) => {
          if (prev >= totalFrames) return 1;
          return prev + 1;
        });
      }, 1000 / (15 * playbackSpeed));
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying, playbackSpeed, totalFrames]);

  const progressPct = (currentFrame / totalFrames) * 100;
  const timeSeconds = (currentFrame / 15).toFixed(1);

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
            setCurrentFrame(1);
            setIsPlaying(false);
          }}
          className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Restart Flight"
          aria-label="Restart flight"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

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
            Frame {currentFrame} / {totalFrames} ({progressPct.toFixed(0)}%)
          </span>
        </div>

        <input
          type="range"
          min="1"
          max={totalFrames}
          value={currentFrame}
          onChange={(e) => setCurrentFrame(parseInt(e.target.value))}
          aria-label="Flight timeline frame scrubber"
          className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
      </div>

      {/* Telemetry Stream Readouts */}
      <div className="hidden lg:flex items-center gap-4 text-[11px] font-mono text-zinc-400 border-l border-zinc-800 pl-4">
        <div>
          <span className="text-zinc-500">LAT:</span> 47.38435° N
        </div>
        <div>
          <span className="text-zinc-500">LON:</span> 8.54518° E
        </div>
        <div>
          <span className="text-zinc-500">ALT:</span> 475.2m
        </div>
        <div className="text-emerald-400 font-semibold">
          <span className="text-zinc-500">MODE:</span> VIO+EKF
        </div>
      </div>
    </footer>
  );
};
