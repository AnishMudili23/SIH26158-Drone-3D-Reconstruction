"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/Header";
import { StatusStrip } from "@/components/StatusStrip";
import { MissionSidebar } from "@/components/MissionSidebar";
import { CesiumViewport } from "@/components/CesiumViewport";
import { StructureInspector } from "@/components/StructureInspector";
import { FlightTimeline } from "@/components/FlightTimeline";
import {
  fetchHealth,
  fetchMissions,
  fetchMissionDetail,
  fetchMissionBuildings,
} from "@/lib/api";
import {
  MissionSummary,
  MissionDetail,
  BuildingInstance,
} from "@/types/mission";

export default function Home() {
  const [missions, setMissions] = useState<MissionSummary[]>([]);
  const [selectedMissionId, setSelectedMissionId] = useState<string>("zurich_mav_mission");
  const [detail, setDetail] = useState<MissionDetail | null>(null);
  const [buildings, setBuildings] = useState<BuildingInstance[]>([]);
  const [systemHealth, setSystemHealth] = useState<{ status: string; gpu_available: boolean; device: string }>({
    status: "checking",
    gpu_available: false,
    device: "unknown",
  });

  // Layer & Visual States
  const [pointCloudVisible, setPointCloudVisible] = useState(true);
  const [trajectoryVisible, setTrajectoryVisible] = useState(true);
  const [colorMode, setColorMode] = useState<"semantic" | "uncertainty">("semantic");
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.4);
  const [selectedBuildingId, setSelectedBuildingId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    const [h, mList, bList] = await Promise.all([
      fetchHealth(),
      fetchMissions(),
      fetchMissionBuildings(selectedMissionId),
    ]);
    setSystemHealth(h);
    setMissions(mList);
    setBuildings(bList);

    const det = await fetchMissionDetail(selectedMissionId);
    setDetail(det);
  }, [selectedMissionId]);

  useEffect(() => {
    loadData();
    setSelectedBuildingId(null);
  }, [loadData]);

  const selectedMission = missions.find((m) => m.id === selectedMissionId) || missions[0];

  return (
    <div className="flex flex-col h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* 1. Top Navigation Bar */}
      <Header
        missions={missions}
        selectedMissionId={selectedMissionId}
        onSelectMission={setSelectedMissionId}
        sensorQuality={selectedMission?.sensor_quality}
        telemetryProvenance={selectedMission?.telemetry_provenance}
        systemHealth={systemHealth}
        onRefresh={loadData}
      />

      <StatusStrip mission={selectedMission} />

      {/* 2. Main 3-Column Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {systemHealth.status !== "online" && missions.length === 0 && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-zinc-950/95">
            <div className="text-center max-w-md px-6">
              <div className="text-red-400 text-lg font-semibold mb-2">
                {systemHealth.status === "checking" ? "Connecting to backend…" : "SYSTEM OFFLINE"}
              </div>
              {systemHealth.status === "offline" && (
                <p className="text-zinc-400 text-sm">
                  Could not reach the reconstruction API at {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}.
                  No mission data is being fabricated — connect the backend to load a mission.
                </p>
              )}
            </div>
          </div>
        )}
        {/* Left Panel: Mission Stats, Sensor Quality, GIS Layers & Deliverables */}
        <MissionSidebar
          mission={selectedMission}
          detail={detail}
          pointCloudVisible={pointCloudVisible}
          onTogglePointCloud={() => setPointCloudVisible(!pointCloudVisible)}
          trajectoryVisible={trajectoryVisible}
          onToggleTrajectory={() => setTrajectoryVisible(!trajectoryVisible)}
          colorMode={colorMode}
          onChangeColorMode={setColorMode}
          confidenceThreshold={confidenceThreshold}
          onChangeConfidenceThreshold={setConfidenceThreshold}
        />

        {/* Center Panel: Cesium 3D Digital Twin with Onboard PiP */}
        <CesiumViewport
          missionId={selectedMissionId}
          colorMode={colorMode}
          confidenceThreshold={confidenceThreshold}
          selectedBuildingId={selectedBuildingId}
          onBuildingSelected={setSelectedBuildingId}
        />

        {/* Right Panel: Discrete Building Instance Inspector & Semantics */}
        <StructureInspector
          buildings={buildings}
          detail={detail}
          semanticQuality={selectedMission?.semantic_quality || detail?.report?.semantic_quality}
          selectedBuildingId={selectedBuildingId}
          onFocusBuilding={(b) => setSelectedBuildingId(b.instance_id)}
        />
      </div>

      {/* 3. Bottom Flight Timeline & Sensor Replay Scrubber */}
      <FlightTimeline
        totalFrames={selectedMission?.total_frames || 0}
      />
    </div>
  );
}
