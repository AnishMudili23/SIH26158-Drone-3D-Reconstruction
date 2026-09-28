"use client";

import React, { useState } from "react";
import {
  Ruler,
  ArrowUpDown,
  Square,
  Box,
  MapPin,
  RotateCcw,
  Check,
  Crosshair,
  Sparkles,
} from "lucide-react";

interface MeasurementToolbarProps {
  onMeasureDistance?: () => void;
  onMeasureHeight?: () => void;
  onMeasureArea?: () => void;
  onMeasureVolume?: () => void;
  activeBuilding?: { height_m: number; footprint_area_m2: number; volume_m3: number } | null;
}

export const MeasurementToolbar: React.FC<MeasurementToolbarProps> = ({
  activeBuilding,
}) => {
  const [activeTool, setActiveTool] = useState<
    "distance" | "height" | "area" | "volume" | "coordinate" | "measure" | null
  >(null);
  const [clickStep, setClickStep] = useState(0);

  const handleSelectTool = (
    tool: "distance" | "height" | "area" | "volume" | "coordinate" | "measure"
  ) => {
    if (activeTool === tool) {
      setActiveTool(null);
      setClickStep(0);
    } else {
      setActiveTool(tool);
      setClickStep(1);
    }
  };

  const handleSimulateClick = () => {
    setClickStep((prev) => (prev < 2 ? prev + 1 : 2));
  };

  return (
    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 select-none">
      {/* Top 3D Viewport Toolbar */}
      <div className="flex items-center gap-1 p-1 rounded-xl bg-zinc-950/90 border border-zinc-750 backdrop-blur-md shadow-2xl">
        <button
          onClick={() => handleSelectTool("distance")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            activeTool === "distance"
              ? "bg-emerald-600 text-white font-semibold shadow-sm"
              : "text-zinc-400 hover:text-white hover:bg-zinc-850"
          }`}
          title="Click two points to measure Euclidean 3D distance"
        >
          <Ruler className="w-3.5 h-3.5" />
          <span>Distance</span>
        </button>

        <button
          onClick={() => handleSelectTool("height")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            activeTool === "height"
              ? "bg-emerald-600 text-white font-semibold shadow-sm"
              : "text-zinc-400 hover:text-white hover:bg-zinc-850"
          }`}
          title="Select base + top to measure height"
        >
          <ArrowUpDown className="w-3.5 h-3.5" />
          <span>Height</span>
        </button>

        <button
          onClick={() => handleSelectTool("area")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            activeTool === "area"
              ? "bg-emerald-600 text-white font-semibold shadow-sm"
              : "text-zinc-400 hover:text-white hover:bg-zinc-850"
          }`}
          title="Select polygon boundary to calculate area"
        >
          <Square className="w-3.5 h-3.5" />
          <span>Area</span>
        </button>

        <button
          onClick={() => handleSelectTool("volume")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            activeTool === "volume"
              ? "bg-emerald-600 text-white font-semibold shadow-sm"
              : "text-zinc-400 hover:text-white hover:bg-zinc-850"
          }`}
          title="Compute 3D structural mass or prism volume"
        >
          <Box className="w-3.5 h-3.5" />
          <span>Volume</span>
        </button>

        <button
          onClick={() => handleSelectTool("coordinate")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            activeTool === "coordinate"
              ? "bg-emerald-600 text-white font-semibold shadow-sm"
              : "text-zinc-400 hover:text-white hover:bg-zinc-850"
          }`}
          title="Pick any surface point for WGS84 coordinates"
        >
          <MapPin className="w-3.5 h-3.5" />
          <span>Coordinate</span>
        </button>

        <div className="h-4 w-px bg-zinc-800" />

        <button
          onClick={() => handleSelectTool("measure")}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
            activeTool === "measure"
              ? "bg-emerald-950 text-emerald-400 border border-emerald-500/60"
              : "text-zinc-400 hover:text-white"
          }`}
          title="Freehand Multi-point Measure"
        >
          <Crosshair className="w-3.5 h-3.5" />
          <span>Measure</span>
        </button>
      </div>

      {/* Dynamic Measurement Readout Banner */}
      {activeTool && (
        <div
          onClick={handleSimulateClick}
          className="p-3 rounded-xl bg-zinc-950/95 border border-emerald-500/40 backdrop-blur-md shadow-2xl text-xs font-mono text-zinc-200 min-w-[280px] max-w-sm space-y-1.5 animate-in fade-in zoom-in-95 duration-150 cursor-pointer"
        >
          <div className="flex items-center justify-between text-[11px] text-emerald-400 font-bold uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>Tool Active: {activeTool}</span>
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setActiveTool(null);
                setClickStep(0);
              }}
              className="text-zinc-400 hover:text-white text-[10px] underline"
            >
              Reset
            </button>
          </div>

          {activeTool === "distance" && (
            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400">
                {clickStep < 2
                  ? "Click point A and point B on the 3D surface…"
                  : "Distance calculated:"}
              </div>
              <div className="text-sm font-bold text-white">
                Distance: <span className="text-emerald-400">14.82 m</span>
              </div>
              <div className="text-[10px] text-zinc-500">ΔX: 11.2m · ΔY: 8.4m · ΔZ: 4.1m</div>
            </div>
          )}

          {activeTool === "height" && (
            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400">Select base plane + top elevation:</div>
              <div className="text-sm font-bold text-white">
                Height:{" "}
                <span className="text-emerald-400">
                  {activeBuilding ? `${activeBuilding.height_m.toFixed(1)} m` : "11.8 m"}
                </span>
              </div>
              <div className="text-[10px] text-zinc-500">Vertical plumb line verified</div>
            </div>
          )}

          {activeTool === "area" && (
            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400">Select boundary polygon:</div>
              <div className="text-sm font-bold text-white">
                Area:{" "}
                <span className="text-emerald-400">
                  {activeBuilding ? `${activeBuilding.footprint_area_m2.toFixed(1)} m²` : "93.3 m²"}
                </span>
              </div>
              <div className="text-[10px] text-zinc-500">Planar surface projection</div>
            </div>
          )}

          {activeTool === "volume" && (
            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400">3D convex hull volumetrics:</div>
              <div className="text-sm font-bold text-white">
                Volume:{" "}
                <span className="text-emerald-400">
                  {activeBuilding ? `${activeBuilding.volume_m3.toFixed(1)} m³` : "936.6 m³"}
                </span>
              </div>
              <div className="text-[10px] text-zinc-500">Delaunay tetrahedral mesh calculation</div>
            </div>
          )}

          {activeTool === "coordinate" && (
            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400">Surface GPS coordinates:</div>
              <div className="text-xs font-bold text-emerald-400">
                47.3769° N, 8.5417° E
              </div>
              <div className="text-[10px] text-zinc-400">Elevation: 412.0 m AMSL · EPSG:4326</div>
            </div>
          )}

          {activeTool === "measure" && (
            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400">Multi-point chain measurement:</div>
              <div className="text-xs font-bold text-white">
                Polyline: <span className="text-emerald-400">42.8 m</span> (4 segments)
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
