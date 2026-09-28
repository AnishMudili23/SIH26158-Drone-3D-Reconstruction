"use client";

import React, { useRef, useEffect } from "react";
import { BuildingInstance, MissionTrajectory } from "@/types/mission";

interface GisMapCanvasProps {
  trajectory: MissionTrajectory | null;
  buildings: BuildingInstance[];
  currentFrame: number;
  totalFrames: number;
  selectedBuildingId?: number | null;
  onSelectBuilding?: (instanceId: number) => void;
}

export const GisMapCanvas: React.FC<GisMapCanvasProps> = ({
  trajectory,
  buildings,
  currentFrame,
  totalFrames,
  selectedBuildingId,
  onSelectBuilding,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let pulse = 0;

    const render = () => {
      pulse += 0.05;
      const w = (canvas.width = canvas.parentElement?.clientWidth || 600);
      const h = (canvas.height = canvas.parentElement?.clientHeight || 500);

      // 1. Dark Background
      ctx.fillStyle = "#05070a";
      ctx.fillRect(0, 0, w, h);

      // 2. Cartographic Coordinate Grid
      ctx.strokeStyle = "rgba(39, 39, 42, 0.45)";
      ctx.lineWidth = 1;
      const gridSize = 40;
      for (let x = 0; x < w; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // Origin center
      const cx = w / 2;
      const cy = h / 2;
      const scale = Math.min(w, h) / 160;

      // 3. Structure Footprints (2D Polygons)
      const mockBuildings = buildings.length > 0 ? buildings : [
        { instance_id: 1, centroid_xyz: [12.4, -4.2, 5.9] as [number, number, number], footprint_area_m2: 93.3 },
        { instance_id: 2, centroid_xyz: [-8.1, 14.5, 3.2] as [number, number, number], footprint_area_m2: 54.2 },
        { instance_id: 3, centroid_xyz: [22.0, 18.3, 2.4] as [number, number, number], footprint_area_m2: 38.6 },
      ];

      mockBuildings.forEach((b) => {
        const bx = cx + (b.centroid_xyz?.[0] || 0) * scale * 2.2;
        const by = cy - (b.centroid_xyz?.[1] || 0) * scale * 2.2;
        const radius = Math.sqrt(b.footprint_area_m2 || 50) * scale * 0.45;
        const isSelected = selectedBuildingId === b.instance_id;

        // Footprint fill
        ctx.fillStyle = isSelected ? "rgba(16, 185, 129, 0.25)" : "rgba(39, 39, 42, 0.75)";
        ctx.strokeStyle = isSelected ? "#10b981" : "#52525b";
        ctx.lineWidth = isSelected ? 2 : 1.2;

        ctx.beginPath();
        ctx.rect(bx - radius, by - radius, radius * 2, radius * 2);
        ctx.fill();
        ctx.stroke();

        // Label
        ctx.fillStyle = isSelected ? "#34d399" : "#a1a1aa";
        ctx.font = "10px monospace";
        ctx.fillText(`Structure #${b.instance_id}`, bx - radius, by - radius - 5);
      });

      // 4. Drone Flight Trajectory Line
      ctx.beginPath();
      ctx.strokeStyle = "#10b981";
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);

      const nPoints = 50;
      let activeX = cx;
      let activeY = cy;

      for (let i = 0; i <= nPoints; i++) {
        const t = (i / nPoints) * Math.PI * 2;
        const tx = cx + Math.cos(t) * 110 * (scale / 3.5);
        const ty = cy + Math.sin(t * 1.5) * 60 * (scale / 3.5);

        if (i === 0) ctx.moveTo(tx, ty);
        else ctx.lineTo(tx, ty);

        // Waypoint capture dots
        if (i % 5 === 0) {
          ctx.fillStyle = "#34d399";
          ctx.fillRect(tx - 2, ty - 2, 4, 4);
        }

        // Active drone point
        const activeIdx = Math.floor((currentFrame / Math.max(totalFrames, 1)) * nPoints);
        if (i === activeIdx) {
          activeX = tx;
          activeY = ty;
        }
      }
      ctx.stroke();
      ctx.setLineDash([]);

      // 5. Active Drone Beacon with Pulse
      ctx.beginPath();
      ctx.arc(activeX, activeY, 6 + Math.sin(pulse) * 3, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(16, 185, 129, 0.6)";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(activeX, activeY, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#10b981";
      ctx.fill();

      // Drone heading indicator
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 9px monospace";
      ctx.fillText("DRONE_01", activeX + 8, activeY - 8);

      // 6. Map Overlays (North Arrow & Scale Bar)
      ctx.fillStyle = "#a1a1aa";
      ctx.font = "10px monospace";
      ctx.fillText("N ↑  47.3769° N, 8.5417° E", 16, 24);

      // Scale bar
      ctx.strokeStyle = "#a1a1aa";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(16, h - 20);
      ctx.lineTo(80, h - 20);
      ctx.stroke();
      ctx.fillText("50 m", 40, h - 26);

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [trajectory, buildings, currentFrame, totalFrames, selectedBuildingId]);

  return (
    <div className="w-full h-full relative overflow-hidden bg-[#05070a] select-none">
      <canvas ref={canvasRef} className="w-full h-full block" />
      <div className="absolute bottom-3 right-3 bg-zinc-950/80 border border-zinc-800 rounded px-2 py-1 text-[10px] font-mono text-zinc-400">
        GIS Topographic Projection · EPSG:2056
      </div>
    </div>
  );
};
