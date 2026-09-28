"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Compass,
  Video,
  Maximize2,
  Minimize2,
  RefreshCcw,
  Eye,
  WifiOff,
  Map as MapIcon,
  Columns,
  Box,
} from "lucide-react";
import { GisMapCanvas } from "./GisMapCanvas";
import { BuildingInstance, MissionTrajectory } from "@/types/mission";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface CesiumViewportProps {
  missionId: string;
  colorMode: "semantic" | "uncertainty";
  confidenceThreshold: number;
  selectedBuildingId?: number | null;
  onBuildingSelected?: (instanceId: number) => void;
  currentFrame?: number;
  totalFrames?: number;
  onFrameChange?: (frame: number) => void;
  trajectory?: MissionTrajectory | null;
  buildings?: BuildingInstance[];
}

export const CesiumViewport: React.FC<CesiumViewportProps> = ({
  missionId,
  colorMode,
  confidenceThreshold,
  selectedBuildingId,
  onBuildingSelected,
  currentFrame = 1,
  totalFrames = 350,
  onFrameChange,
  trajectory = null,
  buildings = [],
}) => {
  const [viewportMode, setViewportMode] = useState<"3D" | "MAP" | "SPLIT">("3D");
  const [videoOpen, setVideoOpen] = useState(true);
  const [videoMinimized, setVideoMinimized] = useState(false);
  const [backendReachable, setBackendReachable] = useState<boolean | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    setVideoUrl(null);
    if (!missionId) return;
    fetch(`${API_BASE}/api/missions/${missionId}/video`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setVideoUrl(data ? `${API_BASE}${data.url}` : null))
      .catch(() => setVideoUrl(null));
  }, [missionId]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const msg = event.data;
      if (msg && msg.type === "buildingSelected" && typeof msg.instance_id === "number") {
        onBuildingSelected?.(msg.instance_id);
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [onBuildingSelected]);

  useEffect(() => {
    if (selectedBuildingId == null) return;
    iframeRef.current?.contentWindow?.postMessage(
      { type: "focusBuilding", instance_id: selectedBuildingId },
      "*"
    );
  }, [selectedBuildingId]);

  // Synchronize Cesium 3D drone position and PiP video playback when timeline scrubs
  useEffect(() => {
    if (currentFrame == null || !totalFrames || totalFrames <= 1) return;

    // 1. Post scrubFrame message to embedded Cesium viewer
    iframeRef.current?.contentWindow?.postMessage(
      { type: "scrubFrame", frameIndex: currentFrame, totalFrames },
      "*"
    );

    // 2. Synchronize PiP video playback position
    if (videoRef.current && videoRef.current.duration && !isNaN(videoRef.current.duration)) {
      const frac = Math.min(Math.max((currentFrame - 1) / Math.max(totalFrames - 1, 1), 0), 1);
      const targetTime = frac * videoRef.current.duration;
      if (Math.abs(videoRef.current.currentTime - targetTime) > 0.15) {
        videoRef.current.currentTime = targetTime;
      }
    }
  }, [currentFrame, totalFrames]);

  const datasetPath = missionId ? `/static/outputs/${missionId}/viewer_data` : "";
  const viewerUrl =
    `${API_BASE}/viewer/cesium_viewer.html?embed=1&mode=${colorMode}` +
    `&cutoff=${confidenceThreshold}` +
    (datasetPath ? `&dataset=${encodeURIComponent(datasetPath)}` : "");

  const checkBackend = React.useCallback(() => {
    setBackendReachable(null);
    fetch(`${API_BASE}/api/health`, { cache: "no-store" })
      .then((res) => setBackendReachable(res.ok))
      .catch(() => setBackendReachable(false));
  }, []);

  useEffect(() => {
    checkBackend();
  }, [checkBackend, missionId]);

  return (
    <div className="flex-1 relative h-full bg-[#05070a] flex flex-col overflow-hidden select-none">
      {/* Viewport Content Area: 3D | MAP | SPLIT */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Side: 3D Scene (visible in 3D and SPLIT) */}
        {(viewportMode === "3D" || viewportMode === "SPLIT") && (
          <div
            className={`h-full relative overflow-hidden transition-all duration-300 ${
              viewportMode === "SPLIT" ? "w-1/2 border-r border-zinc-800" : "w-full"
            }`}
          >
            {backendReachable === false || !missionId ? (
              <div className="w-full h-full flex items-center justify-center bg-zinc-950">
                <div className="text-center max-w-sm px-6">
                  <WifiOff className="w-8 h-8 text-red-400 mx-auto mb-3" />
                  <div className="text-zinc-200 font-semibold mb-1">3D scene unavailable</div>
                  <p className="text-zinc-500 text-sm mb-4">
                    {!missionId ? "No mission selected." : `Backend connection lost (${API_BASE}).`}
                  </p>
                  {missionId && (
                    <button
                      onClick={checkBackend}
                      className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs cursor-pointer"
                    >
                      Retry connection
                    </button>
                  )}
                </div>
              </div>
            ) : backendReachable === true ? (
              <iframe
                ref={iframeRef}
                src={viewerUrl}
                title="Cesium 3D Mission Digital Twin"
                className="w-full h-full border-0"
                allow="accelerometer; autoplay; encrypted-media; gyroscope"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-zinc-500 text-sm">
                Connecting to backend…
              </div>
            )}
          </div>
        )}

        {/* Right Side: 2D GIS Map (visible in MAP and SPLIT) */}
        {(viewportMode === "MAP" || viewportMode === "SPLIT") && (
          <div
            className={`h-full relative overflow-hidden transition-all duration-300 ${
              viewportMode === "SPLIT" ? "w-1/2" : "w-full"
            }`}
          >
            <GisMapCanvas
              trajectory={trajectory}
              buildings={buildings}
              currentFrame={currentFrame}
              totalFrames={totalFrames}
              selectedBuildingId={selectedBuildingId}
              onSelectBuilding={onBuildingSelected}
            />
          </div>
        )}
      </div>

      {/* Floating Viewport Toolbar (Top Left) */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-zinc-950/90 backdrop-blur border border-zinc-750 p-1.5 rounded-xl shadow-2xl text-xs select-none">
        {/* 3D | MAP | SPLIT Switcher */}
        <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-zinc-900 border border-zinc-800 font-mono text-[11px]">
          <button
            onClick={() => setViewportMode("3D")}
            className={`px-2 py-1 rounded-md transition-colors cursor-pointer flex items-center gap-1 ${
              viewportMode === "3D"
                ? "bg-emerald-950 text-emerald-400 font-bold border border-emerald-800/60"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <Box className="w-3 h-3" />
            <span>3D</span>
          </button>
          <button
            onClick={() => setViewportMode("MAP")}
            className={`px-2 py-1 rounded-md transition-colors cursor-pointer flex items-center gap-1 ${
              viewportMode === "MAP"
                ? "bg-emerald-950 text-emerald-400 font-bold border border-emerald-800/60"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <MapIcon className="w-3 h-3" />
            <span>MAP</span>
          </button>
          <button
            onClick={() => setViewportMode("SPLIT")}
            className={`px-2 py-1 rounded-md transition-colors cursor-pointer flex items-center gap-1 ${
              viewportMode === "SPLIT"
                ? "bg-emerald-950 text-emerald-400 font-bold border border-emerald-800/60"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <Columns className="w-3 h-3" />
            <span>SPLIT</span>
          </button>
        </div>

        <div className="h-4 w-px bg-zinc-800" />

        <button
          onClick={() => {
            if (iframeRef.current) iframeRef.current.src = iframeRef.current.src;
          }}
          className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white transition-colors cursor-pointer"
          title="Reset Camera Orientation"
        >
          <Compass className="w-3.5 h-3.5 text-emerald-400" />
          <span>Reset</span>
        </button>

        <button
          onClick={() => setVideoOpen(!videoOpen)}
          disabled={!videoUrl}
          className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors cursor-pointer ${
            !videoUrl
              ? "bg-zinc-900 text-zinc-600 cursor-not-allowed border border-zinc-800"
              : videoOpen
              ? "bg-emerald-600 text-white shadow-sm"
              : "bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300"
          }`}
          title={videoUrl ? "Toggle Synchronized Onboard Camera Video" : "No onboard video for this mission"}
        >
          <Video className="w-3.5 h-3.5" />
          <span>PiP</span>
        </button>
      </div>

      {/* Synchronized Onboard Camera Video Player (PiP Window) */}
      {videoOpen && videoUrl && (
        <div
          className={`absolute top-4 right-4 z-20 bg-zinc-950/95 border border-zinc-700/80 rounded-xl shadow-2xl overflow-hidden backdrop-blur transition-all duration-300 ${
            videoMinimized ? "w-64 h-10" : "w-80 h-56"
          }`}
        >
          {/* PiP Header */}
          <div className="h-8 bg-zinc-900/90 px-3 flex items-center justify-between border-b border-zinc-800 select-none">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-zinc-200">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Onboard Camera</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setVideoMinimized(!videoMinimized)}
                className="p-1 text-zinc-400 hover:text-zinc-200 rounded"
                title={videoMinimized ? "Expand" : "Minimize"}
                aria-label={videoMinimized ? "Expand video" : "Minimize video"}
              >
                {videoMinimized ? <Maximize2 className="w-3 h-3" /> : <Minimize2 className="w-3 h-3" />}
              </button>
            </div>
          </div>

          {/* Video element */}
          {!videoMinimized && (
            <div className="w-full h-[calc(100%-2rem)] bg-black relative">
              <video
                ref={videoRef}
                key={videoUrl}
                src={videoUrl}
                controls
                autoPlay
                loop
                muted
                playsInline
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-1 left-2 text-[10px] font-mono text-zinc-400 bg-black/60 px-1 rounded">
                CAM_0
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
