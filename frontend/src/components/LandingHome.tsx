"use client";

import React, { useState } from "react";
import {
  Compass,
  ArrowRight,
  FolderOpen,
  Play,
  Layers,
  Sparkles,
  Download,
  Building2,
  Cpu,
  ShieldCheck,
  CheckCircle2,
  Box,
  MapPin,
  HardHat,
  Map,
  Activity,
  Microscope,
  RotateCcw,
  Check,
  ChevronDown,
  Terminal,
  Sliders,
  ExternalLink,
} from "lucide-react";
import { MissionSummary } from "@/types/mission";
import { Hero3DCanvas } from "./Hero3DCanvas";
import { PersonaDetailModal, PersonaId } from "./PersonaDetailModal";

interface LandingHomeProps {
  missions: MissionSummary[];
  onStartMission: (initialType?: string) => void;
  onExploreDemo: () => void;
  onOpenMission: (missionId: string) => void;
  onOpenMissionManager?: () => void;
  onClearDemoData?: () => void;
  onEnterStudio?: () => void;
}

const PERSONAS = [
  {
    id: "infrastructure" as PersonaId,
    icon: HardHat,
    title: "Infrastructure",
    desc: "Inspect bridges, buildings, towers and critical assets with automated 3D volumetric and damage audits.",
    focus: "Structures · Damage · Measurements · Evidence",
  },
  {
    id: "survey" as PersonaId,
    icon: Map,
    title: "Survey & Mapping",
    desc: "Generate survey-grade geospatial DSM, DTM, and GIS-ready orthomosaics with sub-centimeter ground accuracy.",
    focus: "Orthomosaic · DSM · DTM · GIS Export",
  },
  {
    id: "disaster" as PersonaId,
    icon: Activity,
    title: "Disaster Response",
    desc: "Rapidly reconstruct affected zones, identify unobstructed ingress routes, and document hazard perimeters.",
    focus: "Rapid 3D · Hazard Zones · Route Clearance",
  },
  {
    id: "research" as PersonaId,
    icon: Microscope,
    title: "Research & Inspection",
    desc: "Analyze multi-view geometry, epipolar ray intersections, bundle adjustment covariance, and raw point clouds.",
    focus: "Point Cloud · Trajectory · Uncertainty",
  },
];

const BUILDING_INSTANCES = [
  {
    id: "01",
    tag: "COMMERCIAL BUILDING A",
    confidence: "0.88",
    height: "11.8 m",
    footprint: "93.3 m²",
    volume: "1,100.9 m³",
    points: "4,210 pts",
    keyframes: ["#17", "#25", "#37", "#44"],
  },
  {
    id: "02",
    tag: "INDUSTRIAL HANGAR B",
    confidence: "0.93",
    height: "14.2 m",
    footprint: "248.5 m²",
    volume: "3,528.7 m³",
    points: "8,940 pts",
    keyframes: ["#52", "#63", "#71", "#88"],
  },
  {
    id: "03",
    tag: "TELECOM RADAR TOWER",
    confidence: "0.96",
    height: "28.4 m",
    footprint: "34.1 m²",
    volume: "968.4 m³",
    points: "2,380 pts",
    keyframes: ["#104", "#112", "#119"],
  },
];

const LAYER_SPECS = {
  ortho: {
    title: "True Orthomosaic (GeoTIFF)",
    gsd: "1.1 cm/px GSD",
    crs: "WGS84 / UTM 32N (EPSG:32632)",
    format: "16-bit Cloud Optimized GeoTIFF",
    channels: "4 Bands (RGB + Near-Infrared)",
    size: "1.24 GB",
    fidelity: "Survey Grade · Sub-Pixel Orthorectified",
  },
  dsm: {
    title: "Digital Surface Model (DSM)",
    gsd: "2.2 cm/px GSD",
    crs: "WGS84 / UTM 32N (EPSG:32632)",
    format: "32-bit Floating Point Elevation GeoTIFF",
    channels: "1 Band (Absolute Z elevation in meters)",
    size: "480 MB",
    fidelity: "± 0.08m Absolute Vertical Accuracy",
  },
  mesh: {
    title: "Textured 3D Polygonal Mesh",
    gsd: "< 12mm Surface Precision",
    crs: "Local Metric ENU & UTM Geo-referenced",
    format: "Wavefront OBJ + MTL + 4K Atlas",
    channels: "Watertight Manifold Triangulation",
    size: "640 MB",
    fidelity: "Sub-Centimeter Feature Triangulation",
  },
  tiles: {
    title: "OGC 3D Tiles (b3dm)",
    gsd: "Multi-LOD Streamable Octree",
    crs: "ECEF / EPSG:4978 WebGL Compliant",
    format: "Batched 3D Model (b3dm) Hierarchy",
    channels: "LOD Levels 0 through 16",
    size: "720 MB",
    fidelity: "60 FPS Fluid Browser Streaming",
  },
};

const FAQS = [
  {
    q: "How does AeroMesh achieve survey-grade accuracy without physical GCPs?",
    a: "AeroMesh utilizes Geo-Constrained Bundle Adjustment (GC-BA) which tightly fuses dual-frequency RTK/GPS positional priors, 6-DOF IMU gyroscopes, and barometric altimeters directly inside the non-linear Levenberg-Marquardt optimizer. This eliminates scale ambiguity and eliminates trajectory drift across long aerial baselines.",
  },
  {
    q: "Can the 3D reconstruction engine run entirely offline on an air-gapped workstation?",
    a: "Yes. AeroMesh is architected with a local-first processing engine. The complete photogrammetry pipeline, Colmap/Ceres BA solver, neural semantic segmenter, and Cesium 3D Tiles generator run locally on GPU-accelerated workstations without requiring cloud uplinks.",
  },
  {
    q: "What export formats are supported for enterprise CAD and GIS systems?",
    a: "AeroMesh provides instant exports in standard geospatial and 3D formats: OGC 3D Tiles (b3dm), georeferenced GeoTIFF (Orthomosaic, DSM, DTM), colored point clouds (LAS/LAZ, PLY), textured 3D meshes (OBJ + MTL, GLB), and ESRI Shapefiles / GeoJSON for structural building footprints.",
  },
  {
    q: "How does the Defensibility Evidence Engine link 3D findings to raw video frames?",
    a: "Every segmented 3D building voxel preserves an epipolar ray index referencing every camera keyframe that observed it. Selecting any structural finding immediately surfaces the exact raw video keyframes with superimposed reprojection cones, establishing tamper-evident traceability for legal and compliance audits.",
  },
];

export const LandingHome: React.FC<LandingHomeProps> = ({
  missions,
  onStartMission,
  onExploreDemo,
  onOpenMission,
  onOpenMissionManager,
  onClearDemoData,
  onEnterStudio,
}) => {
  const [activePersonaModal, setActivePersonaModal] = useState<PersonaId | null>(null);
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(null);
  const [missionPage, setMissionPage] = useState(1);
  const [activeBuildingIndex, setActiveBuildingIndex] = useState(0);
  const [activeLayerPreview, setActiveLayerPreview] = useState<"ortho" | "dsm" | "mesh" | "tiles">("ortho");
  const missionsPerPage = 4;

  const totalMissionPages = Math.max(1, Math.ceil(missions.length / missionsPerPage));
  const currentPageClamped = Math.min(missionPage, totalMissionPages);
  const pagedMissions = missions.slice(
    (currentPageClamped - 1) * missionsPerPage,
    currentPageClamped * missionsPerPage
  );

  const selectedBuilding = BUILDING_INSTANCES[activeBuildingIndex];
  const selectedLayer = LAYER_SPECS[activeLayerPreview];

  return (
    <div
      id="landing-scroll-container"
      className="flex-1 overflow-y-auto bg-[#05070a] text-zinc-100 flex flex-col justify-between selection:bg-emerald-600/30 relative ambient-halo scroll-smooth"
    >
      {/* Ambient background glow accents */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[850px] h-[380px] bg-gradient-to-b from-cyan-500/10 via-emerald-500/5 to-transparent blur-[120px] pointer-events-none -z-10" />
      <div className="absolute top-[800px] right-0 w-[500px] h-[500px] bg-emerald-500/5 blur-[140px] pointer-events-none -z-10" />

      {/* Main Content Wrapper */}
      <div className="relative isolate px-4 sm:px-6 pt-24 pb-24 max-w-6xl mx-auto w-full">
        {/* 1. HERO SECTION */}
        <section id="overview" className="scroll-mt-28 text-center max-w-4xl mx-auto pt-2 pb-10 relative">
          {/* Subtle Rotating Geometric Wireframe Mesh in Background (Career Copilot Style) */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[720px] h-[480px] pointer-events-none opacity-25 -z-10 flex items-center justify-center">
            <svg className="w-full h-full text-emerald-400/40 animate-spin-slow" viewBox="0 0 500 500">
              <polygon points="250,40 460,150 410,400 250,470 90,400 40,150" fill="none" stroke="currentColor" strokeWidth="1" />
              <polygon points="250,40 360,230 250,470 140,230" fill="none" stroke="currentColor" strokeWidth="1" />
              <line x1="250" y1="40" x2="410" y2="400" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 3" />
              <line x1="250" y1="40" x2="90" y2="400" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 3" />
              <line x1="460" y1="150" x2="40" y2="150" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 3" />
              <line x1="360" y1="230" x2="140" y2="230" stroke="currentColor" strokeWidth="1" />
              <circle cx="250" cy="40" r="3.5" fill="#34d399" />
              <circle cx="460" cy="150" r="3.5" fill="#34d399" />
              <circle cx="410" cy="400" r="3.5" fill="#34d399" />
              <circle cx="250" cy="470" r="3.5" fill="#34d399" />
              <circle cx="90" cy="400" r="3.5" fill="#34d399" />
              <circle cx="40" cy="150" r="3.5" fill="#34d399" />
              <circle cx="360" cy="230" r="3.5" fill="#06b6d4" />
              <circle cx="140" cy="230" r="3.5" fill="#06b6d4" />
            </svg>
          </div>

          {/* Status Chip */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-emerald-500/30 bg-emerald-950/40 text-emerald-400 text-[12px] font-mono uppercase tracking-[0.1em] mb-6 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>AEROMESH 3D GEOSPATIAL INTELLIGENCE PLATFORM • ACTIVE</span>
          </div>

          {/* High-Contrast Editorial Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-[68px] font-bold tracking-[-0.025em] text-white mb-6 leading-[1.08] max-w-[960px] mx-auto">
            Autonomous aerial 3D reconstruction crafted for engineers who care about{" "}
            <span className="font-serif italic font-normal text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-300">
              every millimeter.
            </span>
          </h1>

          {/* Subheading */}
          <p className="text-[17px] sm:text-[18px] text-[#9ca3af] max-w-[720px] mx-auto mb-8 leading-[1.6] font-normal">
            Consolidating multi-view photogrammetry, geo-constrained bundle adjustment, semantic building extraction, and survey-grade orthomosaics into one unified, high-precision intelligence platform.
          </p>

          {/* Primary Action Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4 mb-8">
            <button
              onClick={() => (onEnterStudio ? onEnterStudio() : onStartMission())}
              className="h-12 px-8 flex items-center gap-2.5 rounded-full bg-emerald-400 hover:bg-emerald-300 text-zinc-950 font-bold text-[15px] shadow-[0_0_35px_rgba(52,211,153,0.45)] transition-all transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
            >
              <Compass className="w-4 h-4 text-zinc-950 stroke-[2.5]" />
              <span>Launch 3D Studio</span>
              <ArrowRight className="w-4 h-4 text-zinc-950 stroke-[2.5]" />
            </button>

            <button
              onClick={onExploreDemo}
              className="h-12 px-7 flex items-center gap-2 rounded-full bg-zinc-900/90 hover:bg-zinc-800 text-zinc-200 font-semibold text-[14px] border border-zinc-700/80 transition-all cursor-pointer hover:border-zinc-500"
            >
              <Play className="w-4 h-4 text-emerald-400" />
              <span className="font-mono text-xs uppercase tracking-wider">[ Explore Flight Demo ]</span>
            </button>
          </div>

          {/* Trust Metadata Bar with Monospace Dividers */}
          <div className="flex flex-wrap items-center justify-center gap-3 text-[12px] font-mono text-zinc-400 uppercase tracking-[0.12em] pt-2">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              RTK-GRADE ACCURACY
            </span>
            <span className="text-zinc-600">/</span>
            <span className="flex items-center gap-1.5 text-cyan-400">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              GEO-CONSTRAINED BA
            </span>
            <span className="text-zinc-600">/</span>
            <span className="flex items-center gap-1.5 text-zinc-300">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              SEMANTIC EVIDENCE AUDITING
            </span>
          </div>
        </section>

        {/* 2. LIVING 3D HERO VIEWPORT */}
        <section className="my-8">
          <div className="relative rounded-3xl border border-white/10 bg-zinc-950/70 p-2 sm:p-3 overflow-hidden shadow-2xl">
            {/* Viewport Header Bar */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-white/5 text-[11px] font-mono text-zinc-400">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-white font-semibold">VIEWPORT // LIVE 3D RECONSTRUCTION ENGINE</span>
              </div>
              <div className="hidden sm:flex items-center gap-4 text-zinc-500">
                <span>ROTATION: 6-DOF INTERACTIVE</span>
                <span>MESH: EP-SFM DENSE</span>
              </div>
            </div>

            <div className="relative">
              <Hero3DCanvas />
              {/* Overlay Crosshairs (positioned subtly at corners) */}
              <div className="absolute top-3 left-3 text-zinc-600 font-mono text-xs select-none pointer-events-none">+ [47.3769° N, 8.5417° E]</div>
              <div className="absolute top-3 right-3 text-zinc-600 font-mono text-xs select-none pointer-events-none">[ALT: 412.0m AGL] +</div>
            </div>
          </div>
        </section>

        {/* 3. UNIFIED 4-COLUMN METRIC MATRIX (Crosshair 1px Dividers, No Wrapping Glitches) */}
        <section id="metrics" className="scroll-mt-28 my-14">
          <div className="rounded-3xl border border-white/10 bg-zinc-950/80 backdrop-blur-md overflow-hidden shadow-2xl">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-white/10">
              {/* Metric 1 */}
              <div className="p-8 group hover:bg-white/[0.03] transition-colors">
                <div className="text-[52px] sm:text-[56px] font-extrabold text-white tracking-tight leading-none mb-3 flex items-baseline">
                  350<span className="text-emerald-400 ml-1">+</span>
                </div>
                <div className="text-[11px] font-mono text-emerald-400 uppercase tracking-[0.14em] mb-2 whitespace-nowrap">
                  KEYFRAME IMAGES
                </div>
                <p className="text-[13px] text-[#9ca3af] leading-relaxed">
                  Synchronized 4K aerial frames with zero blur and complete multi-angle overlap.
                </p>
              </div>

              {/* Metric 2 */}
              <div className="p-8 group hover:bg-white/[0.03] transition-colors">
                <div className="text-[52px] sm:text-[56px] font-extrabold text-white tracking-tight leading-none mb-3 flex items-baseline">
                  32.4<span className="text-cyan-400 ml-0.5">K</span>
                </div>
                <div className="text-[11px] font-mono text-cyan-400 uppercase tracking-[0.14em] mb-2 whitespace-nowrap">
                  SPARSE 3D TIE POINTS
                </div>
                <p className="text-[13px] text-[#9ca3af] leading-relaxed">
                  Multi-view epipolar geometry with sub-pixel reprojection error (&lt; 0.85px).
                </p>
              </div>

              {/* Metric 3 */}
              <div className="p-8 group hover:bg-white/[0.03] transition-colors">
                <div className="text-[52px] sm:text-[56px] font-extrabold text-white tracking-tight leading-none mb-3 flex items-baseline">
                  99.4<span className="text-emerald-400 ml-0.5">%</span>
                </div>
                <div className="text-[11px] font-mono text-emerald-400 uppercase tracking-[0.14em] mb-2 whitespace-nowrap">
                  BA CONVERGENCE
                </div>
                <p className="text-[13px] text-[#9ca3af] leading-relaxed">
                  Geo-constrained bundle adjustment solver with sensor fusion confidence score.
                </p>
              </div>

              {/* Metric 4 */}
              <div className="p-8 group hover:bg-white/[0.03] transition-colors">
                <div className="text-[52px] sm:text-[56px] font-extrabold text-white tracking-tight leading-none mb-3 flex items-baseline">
                  &lt; 12<span className="text-cyan-400 ml-1 text-3xl font-bold">mm</span>
                </div>
                <div className="text-[11px] font-mono text-cyan-400 uppercase tracking-[0.14em] mb-2 whitespace-nowrap">
                  SPATIAL RESOLUTION
                </div>
                <p className="text-[13px] text-[#9ca3af] leading-relaxed">
                  Survey-grade Ground Sampling Distance (GSD) across all segmented building envelopes.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 4. PLATFORM PHILOSOPHY BANNER */}
        <section className="my-16 text-center max-w-3xl mx-auto px-4">
          <div className="inline-block text-[11px] font-mono text-zinc-500 uppercase tracking-[0.25em] mb-4">
            [ PLATFORM PHILOSOPHY ]
          </div>
          <blockquote className="text-2xl sm:text-3xl lg:text-[34px] font-semibold text-zinc-100 leading-snug tracking-[-0.01em]">
            “We believe aerial spatial intelligence shouldn’t be left to black-box estimates. Every 3D voxel must be backed by{" "}
            <span className="font-serif italic font-normal text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-300">
              verifiable epipolar ray evidence.
            </span>”
          </blockquote>
          <div className="mt-4 text-[11px] font-mono text-zinc-500 uppercase tracking-[0.18em]">
            — FROM UNCALIBRATED DRONE VIDEO TO SURVEY-GRADE TWIN · AEROMESH 3D
          </div>
        </section>

        {/* 5. SHOWCASE MODULE BENTO CARDS (Unified macOS Framing Across All 4) */}
        <section id="systems" className="scroll-mt-28 my-16 space-y-8">
          <div className="text-center max-w-xl mx-auto mb-10">
            <div className="inline-block text-[11px] font-mono text-emerald-400 uppercase tracking-[0.2em] mb-2">
              [ CORE SYSTEM ARCHITECTURE ]
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Engineered for absolute measurement rigor.
            </h2>
          </div>

          {/* MODULE 01: Multi-View SfM & Dense Reconstruction */}
          <div className="rounded-3xl border border-white/10 bg-zinc-950/70 p-6 sm:p-10 shadow-2xl hover:border-emerald-500/30 transition-all">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Left Column: Narrative */}
              <div className="lg:col-span-7 space-y-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700 font-semibold">
                    [ SYSTEM 01 ]
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                    STRUCTURE FROM MOTION
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-800/40">
                    EPIPOLAR GEOMETRY
                  </span>
                </div>

                <h3 className="text-2xl sm:text-3xl lg:text-[32px] font-bold text-white tracking-tight leading-tight">
                  Multi-View Photogrammetry & Epipolar Geometry Engine
                </h3>

                <p className="text-[15px] sm:text-[16px] text-[#9ca3af] leading-relaxed font-normal">
                  Ingest uncalibrated drone camera feeds, extract scale-invariant feature descriptors, and compute rigid camera motion with real-time pose graph optimization and dense 3D point cloud generation.
                </p>

                <ul className="space-y-3 text-[13px] text-zinc-300">
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Sub-pixel reprojection error minimization (&lt; 0.42 px average)</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Automatic outlier rejection via progressive RANSAC 8-point solver</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Instant multi-scale point cloud decimation for high-framerate inspection</span>
                  </li>
                </ul>

                <div className="pt-2">
                  <button
                    onClick={() => (onEnterStudio ? onEnterStudio() : onStartMission())}
                    className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400 hover:text-emerald-300 transition-colors group cursor-pointer"
                  >
                    <span>OPEN 3D POINT CLOUD STUDIO</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>

              {/* Right Column: Live Inset Preview Widget with macOS header */}
              <div className="lg:col-span-5">
                <div className="rounded-2xl border border-white/10 bg-zinc-900/90 p-5 shadow-2xl space-y-4">
                  {/* macOS Titlebar */}
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                    </div>
                    <span className="text-[10px] font-mono text-zinc-400 tracking-wider">SPATIAL_DENSITY_ANALYZER</span>
                    <span className="inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      60 FPS
                    </span>
                  </div>

                  {/* Circular Radial Gauge + Progress Bars Split */}
                  <div className="flex items-center gap-5 pt-1">
                    {/* SVG Radial Meter */}
                    <div className="relative w-28 h-28 flex items-center justify-center shrink-0">
                      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                        <circle
                          cx="50"
                          cy="50"
                          r="42"
                          stroke="rgba(255,255,255,0.08)"
                          strokeWidth="8"
                          fill="transparent"
                        />
                        <circle
                          cx="50"
                          cy="50"
                          r="42"
                          stroke="#10b981"
                          strokeWidth="8"
                          strokeDasharray="264"
                          strokeDashoffset={264 - 264 * 0.942}
                          strokeLinecap="round"
                          fill="transparent"
                        />
                      </svg>
                      <div className="absolute flex flex-col items-center justify-center text-center">
                        <span className="text-2xl font-black text-white font-mono leading-none">
                          94<span className="text-xs font-normal text-emerald-400">%</span>
                        </span>
                        <span className="text-[8px] font-mono text-emerald-400 uppercase tracking-wider mt-1">
                          HIGH MATCH
                        </span>
                      </div>
                    </div>

                    {/* Progress Bars */}
                    <div className="flex-1 space-y-2.5 font-mono text-xs">
                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-zinc-400">Reprojection Residual</span>
                          <span className="text-emerald-400 font-bold">0.42 px</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                          <div className="h-full bg-emerald-400 rounded-full" style={{ width: "92%" }} />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-zinc-400">Keyframe Overlap</span>
                          <span className="text-cyan-400 font-bold">88.5%</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                          <div className="h-full bg-cyan-400 rounded-full" style={{ width: "88%" }} />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-zinc-400">Point Density</span>
                          <span className="text-white font-bold">1.82M/m²</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 rounded-full" style={{ width: "95%" }} />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Feature Descriptor Badges */}
                  <div className="pt-2 flex flex-wrap gap-1.5 font-mono text-[10px]">
                    <span className="px-2 py-0.5 rounded bg-zinc-800/90 text-zinc-300 border border-zinc-700">
                      + SIFT 128-D
                    </span>
                    <span className="px-2 py-0.5 rounded bg-zinc-800/90 text-zinc-300 border border-zinc-700">
                      + FLANN Matcher
                    </span>
                    <span className="px-2 py-0.5 rounded bg-zinc-800/90 text-zinc-300 border border-zinc-700">
                      + RANSAC 8-Pt
                    </span>
                    <span className="px-2 py-0.5 rounded bg-zinc-800/90 text-zinc-300 border border-zinc-700">
                      + Pose Graph
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* MODULE 02: Geo-Constrained Bundle Adjustment & IMU Fusion */}
          <div id="evidence" className="scroll-mt-28 rounded-3xl border border-white/10 bg-zinc-950/70 p-6 sm:p-10 shadow-2xl hover:border-cyan-500/30 transition-all">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Left Column: Narrative */}
              <div className="lg:col-span-7 space-y-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700 font-semibold">
                    [ SYSTEM 02 ]
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                    SENSOR FUSION
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-800/40">
                    NON-LINEAR CERES BA
                  </span>
                </div>

                <h3 className="text-2xl sm:text-3xl lg:text-[32px] font-bold text-white tracking-tight leading-tight">
                  Geo-Constrained Bundle Adjustment & IMU Telemetry
                </h3>

                <p className="text-[15px] sm:text-[16px] text-[#9ca3af] leading-relaxed font-normal">
                  Tightly couple noisy visual odometry with dual-frequency GPS/RTK, barometric altimeters, and 6-DOF IMU gyroscopes using Ceres/Levenberg-Marquardt non-linear optimizers to completely eradicate drift.
                </p>

                <ul className="space-y-3 text-[13px] text-zinc-300">
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>Eliminates loop-closure scale drift across kilometer-scale flights</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>Calculates covariance uncertainty ellipsoids for every keyframe position</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>Dynamic Huber loss weighting against temporary GPS/IMU signal dropouts</span>
                  </li>
                </ul>

                <div className="pt-2">
                  <button
                    onClick={onExploreDemo}
                    className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400 hover:text-cyan-300 transition-colors group cursor-pointer"
                  >
                    <span>INSPECT TRAJECTORY TELEMETRY</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>

              {/* Right Column: Mac-Style Terminal Runner Widget */}
              <div className="lg:col-span-5">
                <div className="rounded-2xl border border-white/10 bg-black/90 p-5 shadow-2xl font-mono text-xs space-y-4">
                  {/* macOS Titlebar */}
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                    </div>
                    <span className="text-[10px] text-zinc-500 tracking-wider">LIVE_TELEMETRY_RUNNER</span>
                    <span className="inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-red-950/80 text-red-400 border border-red-800/40">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-ping" />
                      REC
                    </span>
                  </div>

                  {/* Inset Status Box (Reference UI Style) */}
                  <div className="p-3.5 rounded-xl border border-zinc-800/90 bg-zinc-950/90 space-y-2">
                    <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono">
                      <span>[ KEYFRAME TELEMETRY 142 OF 350 ]</span>
                      <span className="text-emerald-400">CERES LM FIX</span>
                    </div>
                    <p className="text-[11px] text-zinc-200 font-sans italic leading-relaxed">
                      “Dual-frequency RTK fixed solution integrated with 6-DOF IMU quaternion poses at 100Hz with zero drift.”
                    </p>
                  </div>

                  {/* Telemetry Readout */}
                  <div className="space-y-2 text-[11px]">
                    <div className="flex justify-between items-center text-zinc-400">
                      <span>GPS Fix Status</span>
                      <span className="text-emerald-400 font-bold">3D DGPS FIX (14 SATS)</span>
                    </div>
                    <div className="flex justify-between items-center text-zinc-400">
                      <span>Attitude (P/R/Y)</span>
                      <span className="text-cyan-300">+2.1° / -0.4° / 178.6°</span>
                    </div>
                    <div className="flex justify-between items-center text-zinc-400">
                      <span>Barometric Elevation</span>
                      <span className="text-white">412.35 m (± 0.08m)</span>
                    </div>
                    <div className="flex justify-between items-center text-zinc-400">
                      <span>Camera Shutter</span>
                      <span className="text-zinc-300">1/1600s @ f/2.8 ISO 100</span>
                    </div>
                  </div>

                  {/* Scrub Frame Indicator */}
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 space-y-1">
                    <div className="flex justify-between text-[10px] text-zinc-400">
                      <span>KEYFRAME TIMELINE</span>
                      <span className="text-emerald-400">FRAME 142 / 350</span>
                    </div>
                    <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-400 rounded-full" style={{ width: "40.5%" }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* MODULE 03: Automated Semantic Findings & Defensibility Evidence */}
          <div className="rounded-3xl border border-white/10 bg-zinc-950/70 p-6 sm:p-10 shadow-2xl hover:border-emerald-500/30 transition-all">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Left Column: Narrative */}
              <div className="lg:col-span-7 space-y-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700 font-semibold">
                    [ SYSTEM 03 ]
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                    NEURAL MESH SEGMENTATION
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-800/40">
                    STRUCTURAL AUDITING
                  </span>
                </div>

                <h3 className="text-2xl sm:text-3xl lg:text-[32px] font-bold text-white tracking-tight leading-tight">
                  Automated Semantic Segmentation & Structural Findings
                </h3>

                <p className="text-[15px] sm:text-[16px] text-[#9ca3af] leading-relaxed font-normal">
                  Automatically isolate building footprints, compute base-to-peak elevations, footprint perimeters, and volumetric measurements backed by multi-view cross-validation voting.
                </p>

                <ul className="space-y-3 text-[13px] text-zinc-300">
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>3D bounding box regression with polygon perimeter vectorization</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Multi-view semantic voting eliminates transient occlusions and trees</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Defensibility evidence locker connects 3D findings directly to raw video frames</span>
                  </li>
                </ul>

                <div className="pt-2">
                  <button
                    onClick={onExploreDemo}
                    className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400 hover:text-emerald-300 transition-colors group cursor-pointer"
                  >
                    <span>EXPLORE EVIDENCE FINDINGS</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>

              {/* Right Column: Interactive Structural Findings Widget with macOS header */}
              <div className="lg:col-span-5">
                <div className="rounded-2xl border border-white/10 bg-zinc-900/90 p-5 shadow-2xl space-y-4">
                  {/* macOS Titlebar */}
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                    </div>
                    <span className="text-[10px] font-mono text-zinc-400 tracking-wider">
                      SEMANTIC_DEFENSIBILITY_AUDIT
                    </span>
                    <span className="inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
                      ● VERIFIED
                    </span>
                  </div>

                  {/* Interactive Instance Switcher Tabs */}
                  <div className="flex gap-1.5 font-mono text-[10px]">
                    {BUILDING_INSTANCES.map((inst, idx) => (
                      <button
                        key={inst.id}
                        onClick={() => setActiveBuildingIndex(idx)}
                        className={`flex-1 py-1.5 px-2 rounded-lg border transition-all cursor-pointer truncate ${
                          activeBuildingIndex === idx
                            ? "bg-emerald-950/80 border-emerald-500/60 text-emerald-300 font-bold"
                            : "bg-zinc-950/60 border-zinc-800 text-zinc-400 hover:text-white"
                        }`}
                      >
                        #{inst.id} {inst.tag.split(" ")[0]}
                      </button>
                    ))}
                  </div>

                  {/* Instance Header */}
                  <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2.5 pt-1">
                    <div>
                      <div className="text-[10px] font-mono text-zinc-400">DETECTED INSTANCE #{selectedBuilding.id}</div>
                      <div className="text-sm font-bold text-white tracking-wide">{selectedBuilding.tag}</div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/40 font-semibold">
                      {selectedBuilding.confidence} CONFIDENCE
                    </span>
                  </div>

                  {/* 2x2 Data Metrics Grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2.5 rounded-lg bg-zinc-950/70 border border-zinc-800">
                      <div className="text-[10px] text-zinc-500">HEIGHT</div>
                      <div className="text-sm font-bold text-white mt-0.5">{selectedBuilding.height}</div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-zinc-950/70 border border-zinc-800">
                      <div className="text-[10px] text-zinc-500">FOOTPRINT AREA</div>
                      <div className="text-sm font-bold text-white mt-0.5">{selectedBuilding.footprint}</div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-zinc-950/70 border border-zinc-800">
                      <div className="text-[10px] text-zinc-500">TOTAL VOLUME</div>
                      <div className="text-sm font-bold text-white mt-0.5">{selectedBuilding.volume}</div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-zinc-950/70 border border-zinc-800">
                      <div className="text-[10px] text-zinc-500">3D POINT CLOUD</div>
                      <div className="text-sm font-bold text-emerald-400 mt-0.5">{selectedBuilding.points}</div>
                    </div>
                  </div>

                  {/* Contributing Keyframes Footer */}
                  <div className="pt-1 flex items-center justify-between text-[11px] font-mono text-zinc-400 border-t border-zinc-800/60">
                    <span>Contributing Keyframes:</span>
                    <div className="flex gap-1.5">
                      {selectedBuilding.keyframes.map((kf, i) => (
                        <span key={i} className="text-emerald-400 font-bold bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40 text-[10px]">
                          {kf}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* MODULE 04: Geospatial Orthomosaics & GIS Export Suite */}
          <div className="rounded-3xl border border-white/10 bg-zinc-950/70 p-6 sm:p-10 shadow-2xl hover:border-cyan-500/30 transition-all">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Left Column: Narrative */}
              <div className="lg:col-span-7 space-y-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700 font-semibold">
                    [ SYSTEM 04 ]
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-800/40">
                    GEOSPATIAL EXPORT
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/60 text-indigo-400 border border-indigo-800/40">
                    CAD / GIS SUITE
                  </span>
                </div>

                <h3 className="text-2xl sm:text-3xl lg:text-[32px] font-bold text-white tracking-tight leading-tight">
                  Survey-Grade DSM, DTM & GIS-Ready Orthomosaics
                </h3>

                <p className="text-[15px] sm:text-[16px] text-[#9ca3af] leading-relaxed font-normal">
                  Generate true-orthorectified GeoTIFF orthomosaics, Digital Surface Models (DSM), and export production-ready datasets for CAD, Cesium 3D Tiles, LAS/PLY, and OBJ meshes.
                </p>

                <ul className="space-y-3 text-[13px] text-zinc-300">
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>WGS84 / UTM coordinate reprojection conforming to EPSG standards</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>LOD-optimized Cesium 3D Tiles (b3dm) for fluid browser streaming</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>Seamless integration with ArcGIS Pro, QGIS, Autodesk, and Bentley</span>
                  </li>
                </ul>

                <div className="pt-2">
                  <button
                    onClick={onExploreDemo}
                    className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400 hover:text-cyan-300 transition-colors group cursor-pointer"
                  >
                    <span>LAUNCH EXPORT CENTER</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>

              {/* Right Column: Layer Switcher & Live Specs Widget with macOS header */}
              <div className="lg:col-span-5">
                <div className="rounded-2xl border border-white/10 bg-zinc-900/90 p-5 shadow-2xl space-y-4">
                  {/* macOS Titlebar */}
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                    </div>
                    <span className="text-[10px] font-mono text-zinc-400 tracking-wider">
                      GEOSPATIAL_EXPORT_MATRIX
                    </span>
                    <span className="inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/40">
                      EPSG:32632
                    </span>
                  </div>

                  {/* Interactive Tab Chips */}
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <button
                      onClick={() => setActiveLayerPreview("ortho")}
                      className={`p-2 rounded-lg border text-left transition-all cursor-pointer ${
                        activeLayerPreview === "ortho"
                          ? "bg-emerald-950/70 border-emerald-500/60 text-emerald-300 font-bold"
                          : "bg-zinc-950/50 border-zinc-800 text-zinc-400 hover:text-white"
                      }`}
                    >
                      <div className="text-[9px] opacity-70">LAYER 01</div>
                      <div className="truncate">Orthomosaic</div>
                    </button>

                    <button
                      onClick={() => setActiveLayerPreview("dsm")}
                      className={`p-2 rounded-lg border text-left transition-all cursor-pointer ${
                        activeLayerPreview === "dsm"
                          ? "bg-cyan-950/70 border-cyan-500/60 text-cyan-300 font-bold"
                          : "bg-zinc-950/50 border-zinc-800 text-zinc-400 hover:text-white"
                      }`}
                    >
                      <div className="text-[9px] opacity-70">LAYER 02</div>
                      <div className="truncate">DSM Elevation</div>
                    </button>

                    <button
                      onClick={() => setActiveLayerPreview("mesh")}
                      className={`p-2 rounded-lg border text-left transition-all cursor-pointer ${
                        activeLayerPreview === "mesh"
                          ? "bg-emerald-950/70 border-emerald-500/60 text-emerald-300 font-bold"
                          : "bg-zinc-950/50 border-zinc-800 text-zinc-400 hover:text-white"
                      }`}
                    >
                      <div className="text-[9px] opacity-70">LAYER 03</div>
                      <div className="truncate">Textured Mesh</div>
                    </button>

                    <button
                      onClick={() => setActiveLayerPreview("tiles")}
                      className={`p-2 rounded-lg border text-left transition-all cursor-pointer ${
                        activeLayerPreview === "tiles"
                          ? "bg-cyan-950/70 border-cyan-500/60 text-cyan-300 font-bold"
                          : "bg-zinc-950/50 border-zinc-800 text-zinc-400 hover:text-white"
                      }`}
                    >
                      <div className="text-[9px] opacity-70">LAYER 04</div>
                      <div className="truncate">3D Tiles (b3dm)</div>
                    </button>
                  </div>

                  {/* Dynamic Layer Specifications Readout */}
                  <div className="p-3 rounded-xl bg-zinc-950/80 border border-zinc-800/80 font-mono text-xs space-y-2">
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-zinc-500">Selected Layer:</span>
                      <span className="text-emerald-400 font-bold">{selectedLayer.title}</span>
                    </div>
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-zinc-500">Resolution:</span>
                      <span className="text-cyan-300">{selectedLayer.gsd}</span>
                    </div>
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-zinc-500">Coordinate Frame:</span>
                      <span className="text-white">{selectedLayer.crs}</span>
                    </div>
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-zinc-500">Package Size:</span>
                      <span className="text-zinc-300">{selectedLayer.size}</span>
                    </div>
                  </div>

                  {/* Ready for Export Badges */}
                  <div className="pt-1 flex items-center justify-between text-[10px] font-mono text-zinc-500 border-t border-zinc-800/80">
                    <span>FORMAT: {selectedLayer.format}</span>
                    <span className="text-emerald-400 font-bold">● VERIFIED</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 5B. CONTINUOUS 3D INTELLIGENCE PIPELINE FLOW (Inspired by Reference Architecture Flow) */}
        <section className="my-16">
          <div className="text-center max-w-xl mx-auto mb-8">
            <div className="inline-block text-[11px] font-mono text-zinc-500 uppercase tracking-[0.2em] mb-2">
              [ THE PIPELINE ARCHITECTURE ]
            </div>
            <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              The Continuous Aerial Photogrammetry Loop
            </h3>
            <p className="text-xs text-zinc-400 mt-2">
              A deterministic workflow moving methodically from raw uncalibrated video frames to verified spatial truth.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Step 1 */}
            <div className="p-4 rounded-2xl border border-white/10 bg-zinc-950/70 hover:bg-zinc-900/60 hover:border-emerald-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="text-[10px] font-mono text-emerald-400 font-bold mb-2">[ 01 ]</div>
                <div className="text-sm font-bold text-white mb-1">INGEST</div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  4K aerial frames with synchronized GPS/IMU metadata.
                </p>
              </div>
            </div>
            {/* Step 2 */}
            <div className="p-4 rounded-2xl border border-white/10 bg-zinc-950/70 hover:bg-zinc-900/60 hover:border-emerald-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="text-[10px] font-mono text-emerald-400 font-bold mb-2">[ 02 ]</div>
                <div className="text-sm font-bold text-white mb-1">EXTRACT</div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  SIFT 128-D descriptors with FLANN kd-tree matching.
                </p>
              </div>
            </div>
            {/* Step 3 */}
            <div className="p-4 rounded-2xl border border-white/10 bg-zinc-950/70 hover:bg-zinc-900/60 hover:border-cyan-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="text-[10px] font-mono text-cyan-400 font-bold mb-2">[ 03 ]</div>
                <div className="text-sm font-bold text-white mb-1">ALIGN</div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Epipolar geometry & progressive 8-pt RANSAC pose graph.
                </p>
              </div>
            </div>
            {/* Step 4 */}
            <div className="p-4 rounded-2xl border border-white/10 bg-zinc-950/70 hover:bg-zinc-900/60 hover:border-cyan-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="text-[10px] font-mono text-cyan-400 font-bold mb-2">[ 04 ]</div>
                <div className="text-sm font-bold text-white mb-1">OPTIMIZE</div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Ceres LM geo-constrained bundle adjustment with sensor fusion.
                </p>
              </div>
            </div>
            {/* Step 5 */}
            <div className="p-4 rounded-2xl border border-white/10 bg-zinc-950/70 hover:bg-zinc-900/60 hover:border-emerald-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="text-[10px] font-mono text-emerald-400 font-bold mb-2">[ 05 ]</div>
                <div className="text-sm font-bold text-white mb-1">SEGMENT</div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Neural mesh & multi-view semantic structural voting.
                </p>
              </div>
            </div>
            {/* Step 6 */}
            <div className="p-4 rounded-2xl border border-white/10 bg-zinc-950/70 hover:bg-zinc-900/60 hover:border-emerald-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="text-[10px] font-mono text-emerald-400 font-bold mb-2">[ 06 ]</div>
                <div className="text-sm font-bold text-white mb-1">DELIVER</div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  OGC 3D Tiles, GeoTIFF DSM/DTM & CAD-ready formats.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 6. OPERATIONAL PERSONAS */}
        <section className="my-16">
          <div className="text-center max-w-xl mx-auto mb-8">
            <div className="inline-block text-[11px] font-mono text-zinc-500 uppercase tracking-[0.2em] mb-2">
              [ TARGET WORKFLOWS ]
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Calibrated for mission-critical operations.
            </h2>
            <p className="text-xs text-zinc-400 mt-2">
              Click any profile to inspect tailored tools, precision layers, and output standards.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {PERSONAS.map((p) => {
              const Icon = p.icon;
              return (
                <div
                  key={p.id}
                  onClick={() => setActivePersonaModal(p.id)}
                  className="p-6 rounded-3xl border border-white/10 bg-zinc-950/70 hover:bg-zinc-900/80 hover:border-emerald-500/50 transition-all cursor-pointer flex flex-col justify-between group shadow-lg"
                >
                  <div>
                    <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-4 group-hover:scale-105 transition-transform">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="text-base font-bold text-white mb-2 group-hover:text-emerald-300 transition-colors">
                      {p.title}
                    </div>
                    <p className="text-xs text-zinc-400 leading-relaxed mb-6">{p.desc}</p>
                  </div>
                  <div className="pt-3 border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-emerald-400">
                    <span className="truncate pr-1">{p.focus}</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform shrink-0" />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* 7. OPERATIONAL MISSIONS ARCHIVE */}
        <section id="missions" className="scroll-mt-28 my-16 pt-10 border-t border-white/10">
          <div className="flex flex-wrap items-center justify-between mb-6 gap-3">
            <div>
              <div className="text-[11px] font-mono text-emerald-400 uppercase tracking-widest mb-1">
                [ ACTIVE ARCHIVE ]
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white">
                Recent Operational Flights
              </h3>
              <p className="text-xs text-zinc-400">
                Launch any completed drone flight mission into the 3D studio
              </p>
            </div>
            {onOpenMissionManager && (
              <button
                onClick={onOpenMissionManager}
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1.5 transition-colors cursor-pointer font-mono"
              >
                <span>VIEW ALL MISSIONS</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {pagedMissions.map((m) => (
              <div
                key={m.id}
                onClick={() => onOpenMission(m.id)}
                className="p-5 rounded-2xl border border-white/10 bg-zinc-950/70 hover:bg-zinc-900/80 hover:border-emerald-500/50 transition-all cursor-pointer flex items-center justify-between group shadow-lg"
              >
                <div className="space-y-1.5 min-w-0 pr-3">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-zinc-100 text-sm truncate group-hover:text-emerald-300 transition-colors">
                      {m.name}
                    </span>
                    {m.is_demo && (
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                        SIMULATED
                      </span>
                    )}
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40 font-semibold">
                      ● READY
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono">
                    <span>{m.mission_type || "Building"}</span>
                    <span>·</span>
                    <span>{m.total_frames || 350} frames</span>
                    <span>·</span>
                    <span>{m.building_count || 2} structures</span>
                  </div>
                </div>

                <div className="w-8 h-8 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 group-hover:text-emerald-400 group-hover:border-emerald-500/50 transition-all shrink-0">
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalMissionPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                disabled={currentPageClamped <= 1}
                onClick={() => setMissionPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 rounded-lg text-xs font-mono bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
              >
                Prev
              </button>
              <span className="text-xs font-mono text-zinc-500">
                Page {currentPageClamped} of {totalMissionPages}
              </span>
              <button
                disabled={currentPageClamped >= totalMissionPages}
                onClick={() => setMissionPage((p) => Math.min(totalMissionPages, p + 1))}
                className="px-3 py-1 rounded-lg text-xs font-mono bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
              >
                Next
              </button>
            </div>
          )}
        </section>

        {/* 8. ENGINEERING ENDORSEMENTS (With Circular Avatar Monograms) */}
        <section className="my-16">
          <div className="text-center max-w-xl mx-auto mb-10">
            <div className="inline-block text-[11px] font-mono text-zinc-500 uppercase tracking-[0.2em] mb-2">
              [ VERIFIED BY SPECIALISTS ]
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Endorsed by surveyors and structural engineers.
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="p-6 rounded-3xl border border-white/10 bg-zinc-950/70 shadow-lg space-y-4">
              <p className="text-xs sm:text-sm text-zinc-300 leading-relaxed italic">
                “The geo-constrained bundle adjustment solver eliminated the altitude drift we always faced with long bridge spans. The millimeters matter here.”
              </p>
              <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-bold font-mono text-xs flex items-center justify-center shrink-0">
                  CE
                </div>
                <div className="font-mono text-xs">
                  <div className="font-bold text-white">Chief Geospatial Engineer</div>
                  <div className="text-zinc-500 text-[11px]">Alpine Infrastructure Survey</div>
                </div>
              </div>
            </div>

            <div className="p-6 rounded-3xl border border-white/10 bg-zinc-950/70 shadow-lg space-y-4">
              <p className="text-xs sm:text-sm text-zinc-300 leading-relaxed italic">
                “Linking 3D segmented building polygons back to original camera keyframes gives us bulletproof defensibility during insurance assessments.”
              </p>
              <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-400 font-bold font-mono text-xs flex items-center justify-center shrink-0">
                  SI
                </div>
                <div className="font-mono text-xs">
                  <div className="font-bold text-white">Structural Asset Inspector</div>
                  <div className="text-zinc-500 text-[11px]">Industrial Audit Group</div>
                </div>
              </div>
            </div>

            <div className="p-6 rounded-3xl border border-white/10 bg-zinc-950/70 shadow-lg space-y-4">
              <p className="text-xs sm:text-sm text-zinc-300 leading-relaxed italic">
                “Exporting straight into Cesium 3D Tiles and georeferenced GeoTIFF cut our field turnaround time from days to twenty minutes.”
              </p>
              <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-bold font-mono text-xs flex items-center justify-center shrink-0">
                  MD
                </div>
                <div className="font-mono text-xs">
                  <div className="font-bold text-white">UAV Mapping Operations Director</div>
                  <div className="text-zinc-500 text-[11px]">Geodesic Aerial Labs</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 9. DEFENSIBILITY FAQ ACCORDION (With Monospace Number Badges) */}
        <section className="my-16 max-w-3xl mx-auto">
          <div className="text-center mb-8">
            <div className="inline-block text-[11px] font-mono text-emerald-400 uppercase tracking-[0.2em] mb-2">
              [ TECHNICAL SPECIFICATIONS ]
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Answers to technical inquiries.
            </h2>
          </div>

          <div className="space-y-3">
            {FAQS.map((faq, i) => {
              const isOpen = openFaqIndex === i;
              return (
                <div
                  key={i}
                  className="rounded-2xl border border-white/10 bg-zinc-950/70 overflow-hidden transition-all shadow-md"
                >
                  <button
                    onClick={() => setOpenFaqIndex(isOpen ? null : i)}
                    className="w-full px-5 py-4 flex items-center justify-between text-left text-sm font-semibold text-white hover:text-emerald-300 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-emerald-400 text-xs font-bold">[ 0{i + 1} ]</span>
                      <span>{faq.q}</span>
                    </div>
                    <ChevronDown
                      className={`w-4 h-4 text-zinc-400 shrink-0 transition-transform duration-200 ${
                        isOpen ? "rotate-180 text-emerald-400" : ""
                      }`}
                    />
                  </button>
                  {isOpen && (
                    <div className="px-5 pb-5 text-xs text-zinc-400 leading-relaxed border-t border-zinc-800/80 pt-3">
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* 10. BOTTOM CALL-TO-ACTION CARD (Monumental Reference UI Style) */}
        <section className="my-16">
          <div className="relative rounded-3xl border border-emerald-500/30 bg-gradient-to-b from-zinc-950 via-zinc-900 to-[#060a0f] p-8 sm:p-14 text-center overflow-hidden shadow-2xl">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-emerald-500/10 via-transparent to-transparent pointer-events-none" />

            <div className="relative z-10 max-w-3xl mx-auto space-y-4">
              <div className="inline-block text-[11px] font-mono text-emerald-400 uppercase tracking-[0.25em]">
                [ THE BOTTOM LINE ]
              </div>

              <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-tight uppercase font-sans">
                PIXELS ARE EPHEMERAL.
                <br />
                <span className="font-serif italic font-normal normal-case text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-300">
                  Geometry is truth.
                </span>
              </h2>

              <p className="text-sm sm:text-base text-zinc-400 max-w-xl mx-auto leading-relaxed pt-1">
                Autonomous aerial photogrammetry crafted with mathematical rigor for engineers and surveyors who refuse to accept guesswork.
              </p>

              <div className="pt-6 flex flex-wrap justify-center gap-4">
                <button
                  onClick={() => (onEnterStudio ? onEnterStudio() : onStartMission())}
                  className="h-12 px-8 flex items-center gap-2.5 rounded-full bg-emerald-400 hover:bg-emerald-300 text-zinc-950 font-bold text-[15px] shadow-[0_0_35px_rgba(52,211,153,0.45)] transition-all transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
                >
                  <Compass className="w-4 h-4 text-zinc-950 stroke-[2.5]" />
                  <span>Launch 3D Studio</span>
                  <ArrowRight className="w-4 h-4 text-zinc-950 stroke-[2.5]" />
                </button>

                <button
                  onClick={onExploreDemo}
                  className="h-12 px-7 flex items-center gap-2 rounded-full bg-zinc-900/90 hover:bg-zinc-800 text-zinc-200 font-semibold text-[14px] border border-zinc-700/80 transition-all cursor-pointer hover:border-zinc-500"
                >
                  <Play className="w-4 h-4 text-emerald-400" />
                  <span className="font-mono text-xs uppercase tracking-wider">[ Explore Flight Demo ]</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* 11. CATEGORIZED FOOTER */}
        <footer className="pt-12 pb-6 border-t border-white/10 text-xs text-zinc-400">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 mb-10">
            <div>
              <div className="text-[11px] font-mono text-white font-bold uppercase tracking-wider mb-3">
                Platform
              </div>
              <ul className="space-y-2 text-zinc-500">
                <li><a href="#overview" className="hover:text-emerald-400 transition-colors">Overview</a></li>
                <li><a href="#systems" className="hover:text-emerald-400 transition-colors">Photogrammetry Engine</a></li>
                <li><a href="#metrics" className="hover:text-emerald-400 transition-colors">Spatial Precision</a></li>
                <li><a href="#evidence" className="hover:text-emerald-400 transition-colors">Defensibility Locker</a></li>
              </ul>
            </div>

            <div>
              <div className="text-[11px] font-mono text-white font-bold uppercase tracking-wider mb-3">
                AI & Geometry
              </div>
              <ul className="space-y-2 text-zinc-500">
                <li><span className="hover:text-zinc-300">Geo-Constrained BA</span></li>
                <li><span className="hover:text-zinc-300">Semantic Instance Voting</span></li>
                <li><span className="hover:text-zinc-300">Epipolar Ray Inversion</span></li>
                <li><span className="hover:text-zinc-300">6-DOF Pose Graphs</span></li>
              </ul>
            </div>

            <div>
              <div className="text-[11px] font-mono text-white font-bold uppercase tracking-wider mb-3">
                Geospatial Formats
              </div>
              <ul className="space-y-2 text-zinc-500">
                <li><span className="hover:text-zinc-300">OGC 3D Tiles (b3dm)</span></li>
                <li><span className="hover:text-zinc-300">GeoTIFF DSM / DTM</span></li>
                <li><span className="hover:text-zinc-300">LAS / LAZ 1.4</span></li>
                <li><span className="hover:text-zinc-300">ESRI Shapefile / GeoJSON</span></li>
              </ul>
            </div>

            <div>
              <div className="text-[11px] font-mono text-white font-bold uppercase tracking-wider mb-3">
                Operations
              </div>
              <ul className="space-y-2 text-zinc-500">
                <li>
                  <button onClick={() => onStartMission()} className="hover:text-emerald-400 transition-colors cursor-pointer text-left">
                    + Start New Mission
                  </button>
                </li>
                <li>
                  <button onClick={onExploreDemo} className="hover:text-emerald-400 transition-colors cursor-pointer text-left">
                    Explore Zurich Flight
                  </button>
                </li>
                <li>
                  <span className="text-emerald-500 font-mono text-[10px]">API: localhost:8000</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between pt-6 border-t border-zinc-900 text-[11px] text-zinc-600 font-mono">
            <div>AEROMESH 3D // SIH26158 DRONE 3D RECONSTRUCTION ENGINE</div>
            <div>VERIFIED SUB-PIXEL GEOMETRY</div>
          </div>
        </footer>
      </div>

      {/* Interactive Persona Modal */}
      {activePersonaModal && (
        <PersonaDetailModal
          personaId={activePersonaModal}
          isOpen={true}
          onClose={() => setActivePersonaModal(null)}
          onStartMission={(defaultType) => {
            setActivePersonaModal(null);
            onStartMission(defaultType);
          }}
          onExploreDemo={() => {
            setActivePersonaModal(null);
            onExploreDemo();
          }}
        />
      )}
    </div>
  );
};
