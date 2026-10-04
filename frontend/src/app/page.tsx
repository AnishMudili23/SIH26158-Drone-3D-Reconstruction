"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/Header";
import { StatusStrip } from "@/components/StatusStrip";
import { MissionSidebar } from "@/components/MissionSidebar";
import { CesiumViewport } from "@/components/CesiumViewport";
import { StructureInspector } from "@/components/StructureInspector";
import { FlightTimeline } from "@/components/FlightTimeline";
import { MissionCreatorModal } from "@/components/MissionCreatorModal";
import { LandingHome } from "@/components/LandingHome";
import { PipelineWorkflowBar } from "@/components/PipelineWorkflowBar";
import { MissionSummaryModal } from "@/components/MissionSummaryModal";
import { CompareModeModal } from "@/components/CompareModeModal";
import { SignatureMomentOverlay } from "@/components/SignatureMomentOverlay";
import { MissionManagerModal } from "@/components/MissionManagerModal";
import { Export3DModal } from "@/components/Export3DModal";
import { ExportCenterModal } from "@/components/ExportCenterModal";
import { EvidenceCenterModal } from "@/components/EvidenceCenterModal";
import { StructureDetailDrawer } from "@/components/StructureDetailDrawer";
import { CommandPaletteModal } from "@/components/CommandPaletteModal";
import {
  fetchHealth,
  fetchMissions,
  fetchMissionDetail,
  fetchMissionBuildings,
  fetchMissionTrajectory,
  clearDemoMissions,
} from "@/lib/api";
import {
  MissionSummary,
  MissionDetail,
  BuildingInstance,
  MissionTrajectory,
} from "@/types/mission";

export default function Home() {
  const [viewMode, setViewMode] = useState<"home" | "studio">("home");
  const [activeTab, setActiveTab] = useState<"workspace" | "evidence" | "measurements" | "exports">(
    "workspace"
  );
  const [inspectorMode, setInspectorMode] = useState<"world" | "evidence">("world");

  const [missions, setMissions] = useState<MissionSummary[]>([]);
  const [selectedMissionId, setSelectedMissionId] = useState<string>("zurich_mav_mission");
  const [detail, setDetail] = useState<MissionDetail | null>(null);
  const [buildings, setBuildings] = useState<BuildingInstance[]>([]);
  const [trajectory, setTrajectory] = useState<MissionTrajectory | null>(null);
  const [systemHealth, setSystemHealth] = useState<{ status: string; gpu_available: boolean; device: string }>({
    status: "checking",
    gpu_available: false,
    device: "unknown",
  });

  // Modals & Overlays
  const [isCreatorOpen, setIsCreatorOpen] = useState(false);
  const [creatorInitialType, setCreatorInitialType] = useState("Building");
  const [isMissionsManagerOpen, setIsMissionsManagerOpen] = useState(false);
  const [isExport3DOpen, setIsExport3DOpen] = useState(false);
  const [isExportCenterOpen, setIsExportCenterOpen] = useState(false);
  const [isEvidenceCenterOpen, setIsEvidenceCenterOpen] = useState(false);
  const [selectedStructureForDetail, setSelectedStructureForDetail] = useState<BuildingInstance | null>(null);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isSummaryOpen, setIsSummaryOpen] = useState(false);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [isSignatureMomentOpen, setIsSignatureMomentOpen] = useState(false);

  // Layers
  const [pointCloudVisible, setPointCloudVisible] = useState(true);
  const [trajectoryVisible, setTrajectoryVisible] = useState(true);
  const [structuresVisible, setStructuresVisible] = useState(true);
  const [terrainVisible, setTerrainVisible] = useState(false);
  const [damageVisible, setDamageVisible] = useState(false);
  const [uncertaintyVisible, setUncertaintyVisible] = useState(false);

  const [colorMode, setColorMode] = useState<"semantic" | "uncertainty">("semantic");
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.4);
  const [selectedBuildingId, setSelectedBuildingId] = useState<number | null>(null);
  const [currentFrame, setCurrentFrame] = useState<number>(1);

  // Global Ctrl + K keybinding
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [h, mList, bList, traj, det] = await Promise.all([
        fetchHealth(),
        fetchMissions(),
        fetchMissionBuildings(selectedMissionId),
        fetchMissionTrajectory(selectedMissionId),
        fetchMissionDetail(selectedMissionId),
      ]);
      setSystemHealth(h);
      setMissions(mList);
      setBuildings(bList);
      setTrajectory(traj);
      setDetail(det);
    } catch (e) {
      console.error("loadData error:", e);
      setSystemHealth({ status: "offline", gpu_available: false, device: "unknown" });
    }
  }, [selectedMissionId]);

  useEffect(() => {
    loadData();
    setSelectedBuildingId(null);
    setCurrentFrame(1);
  }, [loadData]);

  const selectedMission = missions.find((m) => m.id === selectedMissionId) || missions[0];
  const totalFrames = selectedMission?.total_frames || trajectory?.trajectory?.length || 350;
  const activeBuilding =
    buildings.find((b) => b.instance_id === selectedBuildingId) || buildings[0] || null;

  const handleOpenMission = (mId: string) => {
    setSelectedMissionId(mId);
    setIsSignatureMomentOpen(true);
  };

  const handleExploreDemo = () => {
    setSelectedMissionId("zurich_mav_mission");
    setIsSignatureMomentOpen(true);
  };

  const handleEnterSignatureWorld = () => {
    setIsSignatureMomentOpen(false);
    setViewMode("studio");
  };

  const handleTabChange = (tab: "workspace" | "evidence" | "measurements" | "exports") => {
    setActiveTab(tab);
    if (tab === "evidence") {
      setIsEvidenceCenterOpen(true);
    } else if (tab === "workspace") {
      setViewMode("studio");
      setInspectorMode("world");
    } else if (tab === "measurements") {
      setViewMode("studio");
    } else if (tab === "exports") {
      setIsExportCenterOpen(true);
    }
  };

  const handleClearDemoData = async () => {
    try {
      await clearDemoMissions();
      loadData();
    } catch (e) {
      console.error("Clear demo error:", e);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#05070a] text-zinc-100 overflow-hidden font-sans">
      {/* 1. Top Navigation */}
      <Header
        missions={missions}
        selectedMissionId={selectedMissionId}
        onSelectMission={setSelectedMissionId}
        onNewMission={() => {
          setCreatorInitialType("Building");
          setIsCreatorOpen(true);
        }}
        onOpenMissionsModal={() => setIsMissionsManagerOpen(true)}
        onOpenSearch={() => setIsCommandPaletteOpen(true)}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        activeTab={activeTab}
        onTabChange={handleTabChange}
        sensorQuality={selectedMission?.sensor_quality}
        systemHealth={systemHealth}
        onRefresh={loadData}
      />

      {/* 2. Main View Mode: Landing Home vs Mission Studio */}
      {viewMode === "home" ? (
        <LandingHome
          missions={missions}
          onStartMission={(initialType) => {
            setCreatorInitialType(initialType || "Building");
            setIsCreatorOpen(true);
          }}
          onExploreDemo={handleExploreDemo}
          onOpenMission={handleOpenMission}
          onOpenMissionManager={() => setIsMissionsManagerOpen(true)}
          onClearDemoData={handleClearDemoData}
          onEnterStudio={() => setViewMode("studio")}
        />
      ) : (
        /* MISSION STUDIO (Hero 3D Screen) */
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* Mission Subheader: Title, Building Inspection, Ready badge, ⋯ menu */}
          <PipelineWorkflowBar
            mission={selectedMission}
            detail={detail}
            onOpenOverview={() => setIsSummaryOpen(true)}
            onOpenEvidence={() => setIsEvidenceCenterOpen(true)}
            onOpenMeasurements={() => {
              setViewMode("studio");
              setActiveTab("measurements");
            }}
            onOpenExports={() => setIsExportCenterOpen(true)}
          />

          {/* 3-Column Studio Workspace */}
          <div className="flex-1 flex overflow-hidden relative">
            {systemHealth.status !== "online" && missions.length === 0 && (
              <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/95">
                <div className="text-center max-w-md px-6">
                  <div className="text-emerald-400 text-lg font-semibold mb-2">
                    {systemHealth.status === "checking" ? "Connecting to backend…" : "SYSTEM OFFLINE"}
                  </div>
                  {systemHealth.status === "offline" && (
                    <p className="text-zinc-400 text-sm">
                      Could not reach the reconstruction API at {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Left Panel: Overview & Layers */}
            <MissionSidebar
              mission={selectedMission}
              detail={detail}
              pointCloudVisible={pointCloudVisible}
              onTogglePointCloud={() => setPointCloudVisible(!pointCloudVisible)}
              trajectoryVisible={trajectoryVisible}
              onToggleTrajectory={() => setTrajectoryVisible(!trajectoryVisible)}
              structuresVisible={structuresVisible}
              onToggleStructures={() => setStructuresVisible(!structuresVisible)}
              terrainVisible={terrainVisible}
              onToggleTerrain={() => setTerrainVisible(!terrainVisible)}
              damageVisible={damageVisible}
              onToggleDamage={() => setDamageVisible(!damageVisible)}
              uncertaintyVisible={uncertaintyVisible}
              onToggleUncertainty={() => {
                setUncertaintyVisible(!uncertaintyVisible);
                setColorMode(uncertaintyVisible ? "semantic" : "uncertainty");
              }}
              colorMode={colorMode}
              onChangeColorMode={setColorMode}
              confidenceThreshold={confidenceThreshold}
              onChangeConfidenceThreshold={setConfidenceThreshold}
            />

            {/* Center Hero: Cesium 3D Viewer with Contextual Controls */}
            <div className="flex-1 relative h-full flex flex-col overflow-hidden">
              <CesiumViewport
                missionId={selectedMissionId}
                colorMode={colorMode}
                confidenceThreshold={confidenceThreshold}
                selectedBuildingId={selectedBuildingId}
                onBuildingSelected={setSelectedBuildingId}
                currentFrame={currentFrame}
                totalFrames={totalFrames}
                onFrameChange={setCurrentFrame}
                trajectory={trajectory}
                buildings={buildings}
              />

              {/* Floating Collapsible Flight Replay Drawer at Bottom */}
              <FlightTimeline
                totalFrames={totalFrames}
                trajectory={trajectory}
                mission={selectedMission}
                detail={detail}
                currentFrame={currentFrame}
                onFrameChange={setCurrentFrame}
              />
            </div>

            {/* Right Panel: AEROMESH FINDINGS Intelligence Panel */}
            <StructureInspector
              buildings={buildings}
              detail={detail}
              semanticQuality={selectedMission?.semantic_quality || detail?.report?.semantic_quality}
              selectedBuildingId={selectedBuildingId}
              onFocusBuilding={(b) => setSelectedBuildingId(b.instance_id)}
              onJumpToFrame={setCurrentFrame}
              onOpenEvidenceCenter={(bldgId) => {
                setIsEvidenceCenterOpen(true);
              }}
              onOpenStructureDetail={(bldg) => setSelectedStructureForDetail(bldg)}
            />
          </div>
        </div>
      )}

      {/* 3. New Mission 3-Step Wizard */}
      <MissionCreatorModal
        isOpen={isCreatorOpen}
        onClose={() => setIsCreatorOpen(false)}
        initialMissionType={creatorInitialType}
        onMissionCreated={(newId) => {
          setSelectedMissionId(newId);
          setIsSignatureMomentOpen(true);
          loadData();
        }}
      />

      {/* 4. Dedicated Mission Directory & Management Modal */}
      <MissionManagerModal
        isOpen={isMissionsManagerOpen}
        onClose={() => setIsMissionsManagerOpen(false)}
        missions={missions}
        selectedMissionId={selectedMissionId}
        onSelectMission={(mId) => {
          setSelectedMissionId(mId);
          setIsSignatureMomentOpen(true);
        }}
        onNewMission={() => {
          setCreatorInitialType("Building");
          setIsCreatorOpen(true);
        }}
        onRefresh={loadData}
      />

      {/* 5. Dedicated 3D Model Export Configuration Modal */}
      <Export3DModal
        isOpen={isExport3DOpen}
        onClose={() => setIsExport3DOpen(false)}
        missionId={selectedMissionId}
        missionName={selectedMission?.name}
      />

      {/* 6. Export Center Modal */}
      <ExportCenterModal
        isOpen={isExportCenterOpen}
        onClose={() => setIsExportCenterOpen(false)}
        mission={selectedMission}
      />

      {/* 7. Dedicated Defensible Evidence Center Modal */}
      <EvidenceCenterModal
        isOpen={isEvidenceCenterOpen}
        onClose={() => setIsEvidenceCenterOpen(false)}
        mission={selectedMission}
        buildings={buildings}
        onJumpToFrame={(f) => {
          setCurrentFrame(f);
          setIsEvidenceCenterOpen(false);
          setViewMode("studio");
        }}
      />

      {/* 8. Dedicated Structure Detail Inspection View */}
      <StructureDetailDrawer
        isOpen={!!selectedStructureForDetail}
        onClose={() => setSelectedStructureForDetail(null)}
        building={selectedStructureForDetail}
        onJumpToFrame={(f) => {
          setCurrentFrame(f);
          setViewMode("studio");
        }}
        onAddMeasurement={() => {
          setViewMode("studio");
        }}
      />

      {/* 9. Global Command Palette (Ctrl + K) */}
      <CommandPaletteModal
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        missions={missions}
        buildings={buildings}
        onSelectMission={(mId) => {
          setSelectedMissionId(mId);
          setViewMode("studio");
        }}
        onSelectBuilding={(bId) => {
          setSelectedBuildingId(bId);
          setViewMode("studio");
        }}
        onOpenMeasurements={() => {
          setViewMode("studio");
          setActiveTab("measurements");
        }}
        onOpenEvidence={() => setIsEvidenceCenterOpen(true)}
        onOpenExports={() => setIsExportCenterOpen(true)}
        onNewMission={() => {
          setCreatorInitialType("Building");
          setIsCreatorOpen(true);
        }}
      />

      {/* 10. Mission Summary Modal */}
      <MissionSummaryModal
        isOpen={isSummaryOpen}
        onClose={() => setIsSummaryOpen(false)}
        mission={selectedMission}
        detail={detail}
      />

      {/* 11. Compare Mode Modal */}
      <CompareModeModal
        isOpen={isCompareOpen}
        onClose={() => setIsCompareOpen(false)}
      />

      {/* 12. Signature Moment Transition Overlay */}
      <SignatureMomentOverlay
        isOpen={isSignatureMomentOpen}
        onEnter={handleEnterSignatureWorld}
        missionName={selectedMission?.name}
        structuresCount={buildings.length || 3}
        sceneArea="12,428 m²"
        coverage="87%"
      />
    </div>
  );
}
