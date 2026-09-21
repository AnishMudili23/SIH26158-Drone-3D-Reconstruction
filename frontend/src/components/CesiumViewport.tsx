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
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CesiumViewportProps {
  missionId: string;
  colorMode: "semantic" | "uncertainty";
  confidenceThreshold: number;
  selectedBuildingId?: number | null;
  onBuildingSelected?: (instanceId: number) => void;
}

export const CesiumViewport: React.FC<CesiumViewportProps> = ({
  missionId,
  colorMode,
  confidenceThreshold,
  selectedBuildingId,
  onBuildingSelected,
}) => {
  const [videoOpen, setVideoOpen] = useState(true);
  const [videoMinimized, setVideoMinimized] = useState(false);
  const [backendReachable, setBackendReachable] = useState<boolean | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    setVideoUrl(null);
    if (!missionId) return;
    fetch(`${API_BASE}/api/missions/${missionId}/video`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setVideoUrl(data ? `${API_BASE}${data.url}` : null))
      .catch(() => setVideoUrl(null));
  }, [missionId]);

  // Click-to-select sync with the embedded Cesium scene: a click on a building
  // marker there posts a "buildingSelected" message up to us, which we forward to
  // the Structure Inspector; selecting a structure there flies the 3D camera to it.
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
    <div className="flex-1 relative h-full bg-zinc-950 flex flex-col overflow-hidden">
      {/* Embedded 3D Cesium WebGL Digital Twin */}
      {backendReachable === false || !missionId ? (
        <div className="w-full h-full flex items-center justify-center bg-zinc-950">
          <div className="text-center max-w-sm px-6">
            <WifiOff className="w-8 h-8 text-red-400 mx-auto mb-3" />
            <div className="text-zinc-200 font-semibold mb-1">3D scene unavailable</div>
            <p className="text-zinc-500 text-sm mb-4">
              {!missionId
                ? "No mission selected."
                : `Backend connection lost (${API_BASE}).`}
            </p>
            {missionId && (
              <button
                onClick={checkBackend}
                className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs"
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

      {/* Floating Viewport Toolbar (Top Left) */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-zinc-900/90 backdrop-blur border border-zinc-700/80 p-1.5 rounded-lg shadow-xl text-xs select-none">
        <button
          onClick={() => {
            if (iframeRef.current) iframeRef.current.src = iframeRef.current.src;
          }}
          className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors"
          title="Reset Camera Orientation"
        >
          <Compass className="w-3.5 h-3.5 text-emerald-400" />
          Reset View
        </button>

        <button
          onClick={() => setVideoOpen(!videoOpen)}
          disabled={!videoUrl}
          className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${
            !videoUrl
              ? "bg-zinc-900 text-zinc-600 cursor-not-allowed"
              : videoOpen
              ? "bg-emerald-600 text-white shadow-sm"
              : "bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
          }`}
          title={videoUrl ? "Toggle Synchronized Onboard Camera Video" : "No onboard video for this mission"}
        >
          <Video className="w-3.5 h-3.5" />
          Onboard PiP
        </button>

        <div className="h-4 w-px bg-zinc-700" />

        <div className="flex items-center gap-1 text-[11px] text-zinc-400 font-mono px-1">
          <Eye className="w-3 h-3 text-emerald-400" />
          {colorMode === "semantic" ? "UAVid Classes" : "Uncertainty Heatmap"}
        </div>
      </div>

      {/* Synchronized Onboard Camera Video Player (PiP Window) */}
      {videoOpen && videoUrl && (
        <div
          className={`absolute top-4 right-4 z-20 bg-zinc-950/95 border border-zinc-700/80 rounded-lg shadow-2xl overflow-hidden backdrop-blur transition-all duration-300 ${
            videoMinimized ? "w-64 h-10" : "w-80 h-56"
          }`}
        >
          {/* PiP Header */}
          <div className="h-8 bg-zinc-900/90 px-3 flex items-center justify-between border-b border-zinc-800 select-none">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-zinc-200">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              Onboard Flight Camera (1080p)
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
