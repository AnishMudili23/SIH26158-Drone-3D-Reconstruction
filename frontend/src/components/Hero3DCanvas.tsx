"use client";

import React, { useEffect, useRef, useState } from "react";

interface Point3D {
  x: number;
  y: number;
  z: number;
  color: string;
  size: number;
}

export const Hero3DCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const mouseRef = useRef({ isDown: false, lastX: 0, lastY: 0, rotX: 0.35, rotY: -0.45 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 700);
    let height = (canvas.height = 360);

    const handleResize = () => {
      if (!canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = 360;
    };
    window.addEventListener("resize", handleResize);

    // Generate synthetic 3D points representing a reconstructed scene
    const points: Point3D[] = [];

    // 1. Terrain ground scatter
    for (let i = 0; i < 280; i++) {
      const x = (Math.random() - 0.5) * 420;
      const y = (Math.random() - 0.5) * 260;
      const z = (Math.sin(x * 0.02) + Math.cos(y * 0.02)) * 6;
      points.push({
        x,
        y,
        z,
        color: Math.random() > 0.6 ? "#22c55e" : "#52525b",
        size: Math.random() * 1.5 + 0.8,
      });
    }

    // 2. Main building cluster
    for (let i = 0; i < 180; i++) {
      const bx = (Math.random() - 0.5) * 80 + 30;
      const by = (Math.random() - 0.5) * 70 - 20;
      const bz = Math.random() * 65 + 5;
      points.push({
        x: bx,
        y: by,
        z: bz,
        color: bz > 50 ? "#4ade80" : "#22c55e",
        size: 1.8,
      });
    }

    // 3. Secondary structure cluster
    for (let i = 0; i < 120; i++) {
      const bx = (Math.random() - 0.5) * 55 - 90;
      const by = (Math.random() - 0.5) * 50 + 30;
      const bz = Math.random() * 42 + 4;
      points.push({
        x: bx,
        y: by,
        z: bz,
        color: bz > 30 ? "#86efac" : "#16a34a",
        size: 1.6,
      });
    }

    // Flight path points
    const flightPath: { x: number; y: number; z: number }[] = [];
    const totalFlightSteps = 40;
    for (let i = 0; i <= totalFlightSteps; i++) {
      const t = (i / totalFlightSteps) * Math.PI * 2;
      const fx = Math.cos(t) * 160 + (i - totalFlightSteps / 2) * 2.5;
      const fy = Math.sin(t * 1.5) * 90;
      const fz = 85 + Math.sin(t) * 10;
      flightPath.push({ x: fx, y: fy, z: fz });
    }

    let time = 0;

    const render = () => {
      time += 0.012;
      if (!mouseRef.current.isDown) {
        mouseRef.current.rotY += 0.003;
      }

      ctx.fillStyle = "#05070a";
      ctx.fillRect(0, 0, width, height);

      // Camera projection variables
      const cx = width / 2;
      const cy = height / 2 + 15;
      const fov = 380;

      const cosY = Math.cos(mouseRef.current.rotY);
      const sinY = Math.sin(mouseRef.current.rotY);
      const cosX = Math.cos(mouseRef.current.rotX);
      const sinX = Math.sin(mouseRef.current.rotX);

      const project = (x: number, y: number, z: number) => {
        // Rotate Y
        const x1 = x * cosY - y * sinY;
        const y1 = x * sinY + y * cosY;
        // Rotate X
        const y2 = y1 * cosX - z * sinX;
        const z2 = y1 * sinX + z * cosX;

        const distance = 460 + z2;
        const scale = fov / Math.max(distance, 10);
        return {
          px: cx + x1 * scale,
          py: cy - y2 * scale,
          scale,
          zDepth: z2,
        };
      };

      // 1. Draw subtle isometric ground grid
      ctx.strokeStyle = "rgba(39, 39, 42, 0.4)";
      ctx.lineWidth = 1;
      const gridSize = 200;
      const step = 40;

      for (let gx = -gridSize; gx <= gridSize; gx += step) {
        const p1 = project(gx, -gridSize, 0);
        const p2 = project(gx, gridSize, 0);
        ctx.beginPath();
        ctx.moveTo(p1.px, p1.py);
        ctx.lineTo(p2.px, p2.py);
        ctx.stroke();
      }
      for (let gy = -gridSize; gy <= gridSize; gy += step) {
        const p1 = project(-gridSize, gy, 0);
        const p2 = project(gridSize, gy, 0);
        ctx.beginPath();
        ctx.moveTo(p1.px, p1.py);
        ctx.lineTo(p2.px, p2.py);
        ctx.stroke();
      }

      // 2. Draw flight path polyline (Emerald green)
      ctx.beginPath();
      ctx.strokeStyle = "rgba(34, 197, 94, 0.75)";
      ctx.lineWidth = 1.8;
      flightPath.forEach((pt, idx) => {
        const proj = project(pt.x, pt.y, pt.z);
        if (idx === 0) ctx.moveTo(proj.px, proj.py);
        else ctx.lineTo(proj.px, proj.py);
      });
      ctx.stroke();

      // Draw camera exposure nodes on flight path
      flightPath.forEach((pt, idx) => {
        if (idx % 4 === 0) {
          const proj = project(pt.x, pt.y, pt.z);
          ctx.fillStyle = "#22c55e";
          ctx.beginPath();
          ctx.arc(proj.px, proj.py, 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      // Drone position along the loop
      const droneIdx = Math.floor(((time * 4) % totalFlightSteps));
      const dronePt = flightPath[droneIdx] || flightPath[0];
      const droneProj = project(dronePt.x, dronePt.y, dronePt.z);

      // Draw drone pulsing icon
      ctx.fillStyle = "#ffffff";
      ctx.beginPath();
      ctx.arc(droneProj.px, droneProj.py, 3.5, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = "#22c55e";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(droneProj.px, droneProj.py, 7 + Math.sin(time * 6) * 2, 0, Math.PI * 2);
      ctx.stroke();

      // Drone sight ray pointing down to active building
      const targetBuildingProj = project(30, -20, 30);
      ctx.strokeStyle = "rgba(34, 197, 94, 0.25)";
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(droneProj.px, droneProj.py);
      ctx.lineTo(targetBuildingProj.px, targetBuildingProj.py);
      ctx.stroke();
      ctx.setLineDash([]);

      // 3. Draw 3D point cloud particles
      points.forEach((pt) => {
        const proj = project(pt.x, pt.y, pt.z);
        if (proj.scale > 0) {
          ctx.fillStyle = pt.color;
          ctx.beginPath();
          ctx.arc(proj.px, proj.py, pt.size * proj.scale * 0.9, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      // 4. Draw bounding prism for Main Building
      const bMin = { x: -10, y: -55, z: 0 };
      const bMax = { x: 70, y: 15, z: 65 };
      const corners = [
        project(bMin.x, bMin.y, bMin.z),
        project(bMax.x, bMin.y, bMin.z),
        project(bMax.x, bMax.y, bMin.z),
        project(bMin.x, bMax.y, bMin.z),
        project(bMin.x, bMin.y, bMax.z),
        project(bMax.x, bMin.y, bMax.z),
        project(bMax.x, bMax.y, bMax.z),
        project(bMin.x, bMax.y, bMax.z),
      ];

      // Draw bottom base
      ctx.strokeStyle = "rgba(34, 197, 94, 0.4)";
      ctx.lineWidth = 1;
      const drawQuad = (i1: number, i2: number, i3: number, i4: number) => {
        ctx.beginPath();
        ctx.moveTo(corners[i1].px, corners[i1].py);
        ctx.lineTo(corners[i2].px, corners[i2].py);
        ctx.lineTo(corners[i3].px, corners[i3].py);
        ctx.lineTo(corners[i4].px, corners[i4].py);
        ctx.closePath();
        ctx.stroke();
      };
      drawQuad(0, 1, 2, 3);
      drawQuad(4, 5, 6, 7);
      // Verticals
      for (let i = 0; i < 4; i++) {
        ctx.beginPath();
        ctx.moveTo(corners[i].px, corners[i].py);
        ctx.lineTo(corners[i + 4].px, corners[i + 4].py);
        ctx.stroke();
      }

      // Structure tag label
      const topCenter = project(30, -20, 68);
      ctx.fillStyle = "rgba(10, 14, 20, 0.85)";
      ctx.strokeStyle = "#22c55e";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(topCenter.px - 45, topCenter.py - 22, 90, 18, 4);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 9px monospace";
      ctx.textAlign = "center";
      ctx.fillText("MAIN BUILDING", topCenter.px, topCenter.py - 10);

      animId = requestAnimationFrame(render);
    };

    render();

    // Mouse drag interaction
    const onMouseDown = (e: MouseEvent) => {
      mouseRef.current.isDown = true;
      mouseRef.current.lastX = e.clientX;
      mouseRef.current.lastY = e.clientY;
    };
    const onMouseMove = (e: MouseEvent) => {
      if (!mouseRef.current.isDown) return;
      const dx = e.clientX - mouseRef.current.lastX;
      const dy = e.clientY - mouseRef.current.lastY;
      mouseRef.current.rotY += dx * 0.008;
      mouseRef.current.rotX = Math.max(-0.5, Math.min(1.1, mouseRef.current.rotX - dy * 0.008));
      mouseRef.current.lastX = e.clientX;
      mouseRef.current.lastY = e.clientY;
    };
    const onMouseUp = () => {
      mouseRef.current.isDown = false;
    };

    canvas.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      canvas.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  return (
    <div
      className="relative rounded-2xl border border-zinc-800 bg-[#05070a] overflow-hidden shadow-2xl group cursor-grab active:cursor-grabbing select-none"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <canvas ref={canvasRef} className="w-full h-[360px] block" />

      {/* Floating HUD Badge */}
      <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/70 border border-zinc-800 backdrop-blur text-[11px] font-mono text-zinc-300">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span>LIVE 3D RECONSTRUCTION</span>
      </div>

      <div className="absolute top-4 right-4 flex items-center gap-2 px-2.5 py-1 rounded bg-black/60 border border-zinc-800/80 text-[10px] font-mono text-zinc-500">
        Drag to orbit
      </div>

      {/* Signature Counter Caption Underneath */}
      <div className="border-t border-zinc-850 px-5 py-3 bg-[#070a0f] flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-zinc-300 font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="font-semibold text-white">3D reconstructed</span>
          <span className="text-zinc-650 hidden sm:inline">────────────────</span>
          <span className="text-emerald-400">350 frames → 32K points → 3 structures</span>
        </div>

        <div className="flex items-center gap-3 text-[11px] text-zinc-400 font-mono">
          <span>Camera: ENU local</span>
          <span>·</span>
          <span>Scale: 1.000x metric</span>
        </div>
      </div>
    </div>
  );
};
