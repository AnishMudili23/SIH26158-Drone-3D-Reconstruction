"use client";

import React from "react";
import {
  X,
  HardHat,
  Map,
  Activity,
  Microscope,
  ArrowRight,
  CheckCircle2,
  Box,
  Layers,
  Ruler,
  ShieldCheck,
  FileSpreadsheet,
  Cpu,
  Compass,
} from "lucide-react";

export type PersonaId = "infrastructure" | "survey" | "disaster" | "research";

interface PersonaConfig {
  id: PersonaId;
  name: string;
  badge: string;
  icon: React.ElementType;
  tagline: string;
  workflow: string[];
  tools: { title: string; desc: string }[];
  defaultMissionType: string;
  missionCta: string;
}

const PERSONA_DATA: Record<PersonaId, PersonaConfig> = {
  infrastructure: {
    id: "infrastructure",
    name: "Infrastructure Inspection",
    badge: "Structural Engineering",
    icon: HardHat,
    tagline:
      "Inspect bridges, buildings, roads, and critical industrial assets using drone-derived 3D reconstruction.",
    workflow: ["Capture", "Reconstruct", "Inspect", "Measure", "Export"],
    tools: [
      { title: "3D Reconstruction", desc: "Monocular video & calibrated sensor SfM mesh" },
      { title: "Structure Detection", desc: "Automated volumetric building & prism discovery" },
      { title: "Damage / Inspection Layer", desc: "Crack, wear, and structural anomaly overlays" },
      { title: "Metric Measurements", desc: "Millimeter-grade distance, height, and area tools" },
      { title: "Evidence Capture", desc: "Frame-by-frame multi-view defensibility audit" },
      { title: "GIS & CAD Export", desc: "Direct GLB, PLY, OBJ, and LAS point cloud export" },
    ],
    defaultMissionType: "Building",
    missionCta: "Start an Infrastructure Mission →",
  },
  survey: {
    id: "survey",
    name: "Survey & Mapping",
    badge: "Geospatial Cartography",
    icon: Map,
    tagline:
      "Generate survey-grade geospatial DSM, DTM, and GIS-ready orthomosaics with verified ground accuracy.",
    workflow: ["Flight Plan", "GCP Sync", "Orthomosaic", "DSM / DTM", "GIS Export"],
    tools: [
      { title: "Orthomosaic Generation", desc: "Georeferenced orthographic top-down imagery" },
      { title: "DSM / DTM Elevation", desc: "Digital surface and terrain models with contour data" },
      { title: "GPS Trajectory Verification", desc: "RTK/PPK GNSS baseline-to-noise validation" },
      { title: "Ground Measurements", desc: "Polygon boundary areas, volumes, and slope cuts" },
      { title: "GIS Deliverable Package", desc: "GeoTIFF, LAS, shapefile metadata bundle" },
      { title: "Mapping Accuracy Audit", desc: "Horizontal and vertical RMSE quality checks" },
    ],
    defaultMissionType: "Terrain",
    missionCta: "Start a Survey & Mapping Mission →",
  },
  disaster: {
    id: "disaster",
    name: "Disaster Response",
    badge: "Rapid Situational Awareness",
    icon: Activity,
    tagline:
      "Rapidly reconstruct storm, earthquake, or flood zones to detect affected areas, clear access routes, and prioritize response.",
    workflow: ["Rapid Ingest", "Fast Mesh", "Hazard Mapping", "Route Clearance", "Evac Package"],
    tools: [
      { title: "Rapid Reconstruction", desc: "Optimized single-pass keyframe mesh generation" },
      { title: "Affected-Area Detection", desc: "Automated perimeter estimation and footprint shifts" },
      { title: "Damage Assessment", desc: "Debris volume estimation and structural compromise scores" },
      { title: "Accessible Routes", desc: "Clear transit corridor identification over terrain" },
      { title: "Before / After Comparison", desc: "Pre-event baseline overlay with delta analysis" },
      { title: "Evidence Package", desc: "NTRO-grade audit export for emergency authorities" },
    ],
    defaultMissionType: "Disaster Area",
    missionCta: "Start a Disaster Response Mission →",
  },
  research: {
    id: "research",
    name: "Research & Inspection",
    badge: "Scientific Photogrammetry",
    icon: Microscope,
    tagline:
      "Analyze multi-view geometry, camera observations, bundle adjustment uncertainty, and research-grade point clouds.",
    workflow: ["Calibration", "Keyframe Filtering", "Bundle Adjustment", "Uncertainty", "Research Export"],
    tools: [
      { title: "Scientific Point Cloud", desc: "Sub-millimeter classified 3D point cloud with RGB" },
      { title: "Multi-View Evidence", desc: "Observer ray agreement and viewing angles per vertex" },
      { title: "Uncertainty Heatmap", desc: "Per-point covariance and confidence visualizer" },
      { title: "Camera Observations", desc: "Intrinsic & extrinsic parameter verification" },
      { title: "Precision Measurement Tools", desc: "Euclidean, polyline, and coordinate readouts" },
      { title: "Research Export", desc: "Raw COLMAP databases, camera poses, and JSON metrics" },
    ],
    defaultMissionType: "Industrial Site",
    missionCta: "Start a Research Mission →",
  },
};

interface PersonaDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  personaId: PersonaId | null;
  onStartMission: (initialType: string) => void;
  onExploreDemo: () => void;
}

export const PersonaDetailModal: React.FC<PersonaDetailModalProps> = ({
  isOpen,
  onClose,
  personaId,
  onStartMission,
  onExploreDemo,
}) => {
  if (!isOpen || !personaId) return null;

  const data = PERSONA_DATA[personaId] || PERSONA_DATA.infrastructure;
  const Icon = data.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-[#080b10] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden text-zinc-100 flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-zinc-850 flex items-start justify-between bg-zinc-950/60">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <Icon className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
                  {data.badge}
                </span>
                <span className="text-xs text-zinc-500 font-mono">AeroMesh_3D Domain Profile</span>
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">{data.name}</h2>
              <p className="text-xs text-zinc-400 mt-1 max-w-lg leading-relaxed">{data.tagline}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {/* Typical Workflow */}
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-2.5 font-bold flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-emerald-400" />
              <span>Typical Workflow</span>
            </div>
            <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 font-mono text-xs text-zinc-300">
              {data.workflow.map((step, idx) => (
                <React.Fragment key={step}>
                  <span className="px-2.5 py-1 rounded-md bg-zinc-800/90 border border-zinc-700/60 text-white font-medium">
                    {step}
                  </span>
                  {idx < data.workflow.length - 1 && (
                    <span className="text-emerald-400 font-bold">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Available Tools */}
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-2.5 font-bold flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              <span>Available Tools & Layers</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {data.tools.map((tool) => (
                <div
                  key={tool.title}
                  className="p-3 rounded-xl bg-zinc-900/40 border border-zinc-850 hover:border-zinc-750 transition-colors"
                >
                  <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200 mb-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{tool.title}</span>
                  </div>
                  <div className="text-[11px] text-zinc-400 leading-normal pl-5.5">
                    {tool.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-zinc-850 bg-zinc-950/80 flex items-center justify-between gap-3">
          <button
            onClick={() => {
              onClose();
              onExploreDemo();
            }}
            className="px-4 py-2.5 rounded-xl border border-zinc-750 bg-zinc-900 hover:bg-zinc-850 text-zinc-300 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
          >
            Explore with Demo Dataset
          </button>

          <button
            onClick={() => {
              onClose();
              onStartMission(data.defaultMissionType);
            }}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/25 transition-all transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
          >
            <span>{data.missionCta}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
