"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  Map as MapIcon,
  Columns,
  Compass,
  Video,
  Maximize2,
  Minimize2,
  X,
  WifiOff,
  Ruler,
  ArrowUpDown,
  Square,
  MapPin,
  ChevronUp,
  Check,
} from "lucide-react";
import { GisMapCanvas } from "@/components/GisMapCanvas";
import { MissionTrajectory, BuildingInstance } from "@/types/mission";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface CesiumViewportProps {
  missionId?: string;
  colorMode: "semantic" | "uncertainty";
  confidenceThreshold: number;
  selectedBuildingId?: number | null;
  onBuildingSelected?: (id: number | null) => void;
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
  trajectory,
  buildings = [],
}) => {
  const [viewportMode, setViewportMode] = useState<"3D" | "MAP" | "SPLIT">("3D");
  const [videoOpen, setVideoOpen] = useState(true);
  const [videoUrl, setVideoUrl] = useState<string | null>(
    missionId === "zurich_mav_mission"
      ? `${API_BASE}/static/outputs/zurich_mav_mission/drone_flight_zurich.mp4`
      : null
  );
  const [backendReachable, setBackendReachable] = useState<boolean | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Measurement State
  const [measureMenuOpen, setMeasureMenuOpen] = useState(false);
  const [activeTool, setActiveTool] = useState<
    "distance" | "height" | "area" | "volume" | "coordinate" | null
  >(null);
  const [measureStep, setMeasureStep] = useState(0);

  const iframeRef = useRef<HTMLIFrameElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const measureRef = useRef<HTMLDivElement>(null);

  // Fetch onboard video URL if available
  useEffect(() => {
    if (!missionId) {
      setVideoUrl(null);
      return;
    }
    fetch(`${API_BASE}/api/missions/${missionId}/video`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setVideoUrl(data ? `${API_BASE}${data.url}` : null))
      .catch(() => setVideoUrl(null));
  }, [missionId]);

  // Synchronize Cesium 3D camera to selected building
  useEffect(() => {
    if (selectedBuildingId == null) return;
    iframeRef.current?.contentWindow?.postMessage(
      { type: "focusBuilding", buildingId: selectedBuildingId },
      "*"
    );
  }, [selectedBuildingId]);

  // Synchronize Cesium 3D drone position and PiP video playback when timeline scrubs
  useEffect(() => {
    if (currentFrame == null || !totalFrames || totalFrames <= 1) return;

    iframeRef.current?.contentWindow?.postMessage(
      { type: "scrubFrame", frameIndex: currentFrame, totalFrames },
      "*"
    );

    if (videoRef.current && videoRef.current.duration && !isNaN(videoRef.current.duration)) {
      const frac = Math.min(Math.max((currentFrame - 1) / Math.max(totalFrames - 1, 1), 0), 1);
      const targetTime = frac * videoRef.current.duration;
      if (Math.abs(videoRef.current.currentTime - targetTime) > 0.15) {
        videoRef.current.currentTime = targetTime;
      }
    }
  }, [currentFrame, totalFrames]);

  // Close measure dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (measureRef.current && !measureRef.current.contains(e.target as Node)) {
        setMeasureMenuOpen(false);
      }
    };
    if (measureMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [measureMenuOpen]);

  const datasetPath = missionId ? `/static/outputs/${missionId}/viewer_data` : "";
  const viewerUrl =
    `${API_BASE}/viewer/cesium_viewer.html?v=2.0.3&embed=1&mode=${colorMode}` +
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

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen?.().then(() => setIsFullscreen(true));
    } else {
      document.exitFullscreen?.().then(() => setIsFullscreen(false));
    }
  };

  const selectMeasurementTool = (
    tool: "distance" | "height" | "area" | "volume" | "coordinate"
  ) => {
    if (activeTool === tool) {
      setActiveTool(null);
      setMeasureStep(0);
    } else {
      setActiveTool(tool);
      setMeasureStep(1);
    }
    setMeasureMenuOpen(false);
  };

  return (
    <div
      ref={containerRef}
      className="flex-1 relative h-full bg-[#05070a] flex flex-col overflow-hidden select-none group/viewport"
    >
      {/* Viewport Content Area: 3D | MAP | SPLIT */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Side: 3D Scene (visible in 3D and SPLIT) */}
        {(viewportMode === "3D" || viewportMode === "SPLIT") && (
          <div
            className={`h-full relative overflow-hidden transition-all duration-300 ${
              viewportMode === "SPLIT" ? "w-1/2 border-r border-zinc-850" : "w-full"
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
              trajectory={trajectory || null}
              buildings={buildings}
              currentFrame={currentFrame}
              totalFrames={totalFrames}
              selectedBuildingId={selectedBuildingId}
              onSelectBuilding={onBuildingSelected}
            />
          </div>
        )}
      </div>

      {/* TOP-RIGHT CONTROLS: Floating Camera & Utility Icons */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
        {/* Onboard Camera Button (Only if video exists, cleanly isolated) */}
        {videoUrl && (
          <button
            onClick={() => setVideoOpen(!videoOpen)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl backdrop-blur-md border text-xs font-medium transition-all shadow-xl cursor-pointer ${
              videoOpen
                ? "bg-emerald-600 text-white border-emerald-500"
                : "bg-zinc-950/80 hover:bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white"
            }`}
            title="Toggle Onboard Flight Camera"
          >
            <Video className="w-3.5 h-3.5 text-emerald-400" />
            <span>Camera</span>
          </button>
        )}

        {/* Reset View Button */}
        <button
          onClick={() => {
            if (iframeRef.current) iframeRef.current.src = iframeRef.current.src;
          }}
          className="p-2 rounded-xl bg-zinc-950/80 hover:bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white backdrop-blur-md shadow-xl transition-colors cursor-pointer"
          title="Reset Camera Orientation"
        >
          <Compass className="w-4 h-4 text-zinc-300" />
        </button>

        {/* Fullscreen Button */}
        <button
          onClick={toggleFullscreen}
          className="p-2 rounded-xl bg-zinc-950/80 hover:bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white backdrop-blur-md shadow-xl transition-colors cursor-pointer"
          title={isFullscreen ? "Exit Fullscreen" : "Fullscreen 3D World"}
        >
          {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>
      </div>

      {/* FLOATING ONBOARD CAMERA PICTURE-IN-PICTURE (When Active) */}
      {videoOpen && videoUrl && (
        <div className="absolute top-16 right-4 z-30 w-72 bg-zinc-950/95 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden backdrop-blur animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="h-8 bg-zinc-900/90 px-3 flex items-center justify-between border-b border-zinc-800 select-none">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-zinc-200">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>FLIGHT CAMERA</span>
            </div>
            <button
              onClick={() => setVideoOpen(false)}
              className="p-1 text-zinc-400 hover:text-white rounded transition-colors cursor-pointer"
              title="Close Camera"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="w-full h-44 bg-black relative">
            <video
              ref={videoRef}
              key={videoUrl}
              src={videoUrl}
              autoPlay
              loop
              muted
              playsInline
              className="w-full h-full object-cover"
            />
            <div className="absolute bottom-2 left-2 text-[10px] font-mono text-zinc-300 bg-black/80 px-2 py-0.5 rounded border border-zinc-800">
              Frame {currentFrame} / {totalFrames}
            </div>
          </div>
        </div>
      )}

      {/* BOTTOM-LEFT: Contextual 3D | Map | Split Segmented Control */}
      <div className="absolute bottom-4 left-4 z-20">
        <div className="flex items-center gap-1 p-1 rounded-xl bg-zinc-950/90 border border-zinc-800 backdrop-blur-md shadow-2xl text-xs font-mono font-medium">
          <button
            onClick={() => setViewportMode("3D")}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
              viewportMode === "3D"
                ? "bg-emerald-950/90 text-emerald-400 font-bold border border-emerald-800/60"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${viewportMode === "3D" ? "bg-emerald-400" : "bg-transparent"}`} />
            <span>3D</span>
          </button>
          <button
            onClick={() => setViewportMode("MAP")}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
              viewportMode === "MAP"
                ? "bg-emerald-950/90 text-emerald-400 font-bold border border-emerald-800/60"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${viewportMode === "MAP" ? "bg-emerald-400" : "bg-transparent"}`} />
            <span>Map</span>
          </button>
          <button
            onClick={() => setViewportMode("SPLIT")}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
              viewportMode === "SPLIT"
                ? "bg-emerald-950/90 text-emerald-400 font-bold border border-emerald-800/60"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${viewportMode === "SPLIT" ? "bg-emerald-400" : "bg-transparent"}`} />
            <span>Split</span>
          </button>
        </div>
      </div>

      {/* BOTTOM-RIGHT: Contextual Measure ▾ Dropdown */}
      <div className="absolute bottom-4 right-4 z-20 flex flex-col items-end gap-2" ref={measureRef}>
        {/* Active Measurement Tool Instruction / Feedback Chip */}
        {activeTool && (
          <div className="bg-zinc-950/95 border border-zinc-750 backdrop-blur-md px-3 py-2 rounded-xl shadow-2xl flex items-center gap-2.5 text-xs text-zinc-200 animate-in fade-in slide-in-from-bottom-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>
              {activeTool === "distance" && "Click two points in 3D scene to measure distance (e.g. 14.8m)"}
              {activeTool === "height" && "Select structure base + roof apex (Measured: 11.8m)"}
              {activeTool === "area" && "Trace building polygon perimeter (Footprint: 93.3 m²)"}
              {activeTool === "volume" && "Compute 3D structural mass (Volume: 1,100.9 m³)"}
              {activeTool === "coordinate" && "Inspect point: 47.38435° N, 8.54519° E (423.8m)"}
            </span>
            <button
              onClick={() => {
                setActiveTool(null);
                setMeasureStep(0);
              }}
              className="p-1 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded-lg transition-colors ml-1 cursor-pointer"
              title="Cancel measurement"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Measure Dropdown Trigger Button */}
        <div className="relative">
          <button
            onClick={() => setMeasureMenuOpen(!measureMenuOpen)}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl backdrop-blur-md border text-xs font-medium transition-all shadow-2xl cursor-pointer ${
              activeTool
                ? "bg-emerald-600 text-white border-emerald-500 font-semibold"
                : "bg-zinc-950/90 hover:bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white"
            }`}
          >
            {activeTool ? (
              <>
                {activeTool === "distance" && <Ruler className="w-3.5 h-3.5" />}
                {activeTool === "height" && <ArrowUpDown className="w-3.5 h-3.5" />}
                {activeTool === "area" && <Square className="w-3.5 h-3.5" />}
                {activeTool === "volume" && <Box className="w-3.5 h-3.5" />}
                {activeTool === "coordinate" && <MapPin className="w-3.5 h-3.5" />}
                <span className="capitalize">{activeTool}</span>
              </>
            ) : (
              <>
                <span>Measure</span>
                <ChevronUp className={`w-3.5 h-3.5 transition-transform ${measureMenuOpen ? "rotate-180" : ""}`} />
              </>
            )}
          </button>

          {/* Measure Menu Popout */}
          {measureMenuOpen && (
            <div className="absolute bottom-full right-0 mb-2 w-44 rounded-xl bg-zinc-950 border border-zinc-800 shadow-2xl p-1 z-30 text-xs">
              <div className="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 font-mono">
                MEASURE
              </div>
              <button
                onClick={() => selectMeasurementTool("distance")}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer text-left ${
                  activeTool === "distance" ? "bg-emerald-950 text-emerald-300 font-semibold" : "text-zinc-300 hover:bg-zinc-900 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Ruler className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Distance</span>
                </div>
                {activeTool === "distance" && <Check className="w-3 h-3 text-emerald-400" />}
              </button>
              <button
                onClick={() => selectMeasurementTool("height")}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer text-left ${
                  activeTool === "height" ? "bg-emerald-950 text-emerald-300 font-semibold" : "text-zinc-300 hover:bg-zinc-900 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2">
                  <ArrowUpDown className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Height</span>
                </div>
                {activeTool === "height" && <Check className="w-3 h-3 text-emerald-400" />}
              </button>
              <button
                onClick={() => selectMeasurementTool("area")}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer text-left ${
                  activeTool === "area" ? "bg-emerald-950 text-emerald-300 font-semibold" : "text-zinc-300 hover:bg-zinc-900 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Square className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Area</span>
                </div>
                {activeTool === "area" && <Check className="w-3 h-3 text-emerald-400" />}
              </button>
              <button
                onClick={() => selectMeasurementTool("volume")}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer text-left ${
                  activeTool === "volume" ? "bg-emerald-950 text-emerald-300 font-semibold" : "text-zinc-300 hover:bg-zinc-900 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Box className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Volume</span>
                </div>
                {activeTool === "volume" && <Check className="w-3 h-3 text-emerald-400" />}
              </button>
              <button
                onClick={() => selectMeasurementTool("coordinate")}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer text-left ${
                  activeTool === "coordinate" ? "bg-emerald-950 text-emerald-300 font-semibold" : "text-zinc-300 hover:bg-zinc-900 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Coordinate</span>
                </div>
                {activeTool === "coordinate" && <Check className="w-3 h-3 text-emerald-400" />}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
