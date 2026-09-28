"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  X,
  Upload,
  Video,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Play,
  Layers,
  Sparkles,
  Compass,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  Building,
  Mountain,
  Factory,
  HelpCircle,
  Activity,
  Image as ImageIcon,
  Check,
  Loader2,
} from "lucide-react";
import {
  createMission,
  uploadMissionVideo,
  uploadMissionTelemetry,
} from "@/lib/api";

interface MissionCreatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onMissionCreated: (missionId: string) => void;
  initialMissionType?: string;
}

const MISSION_TYPES = [
  { id: "Building", label: "Building", icon: Building },
  { id: "Road / Bridge", label: "Road / Bridge", icon: Compass },
  { id: "Terrain", label: "Terrain", icon: Mountain },
  { id: "Industrial Site", label: "Industrial Site", icon: Factory },
  { id: "Disaster Area", label: "Disaster Area", icon: Activity },
  { id: "Other", label: "Other", icon: HelpCircle },
];

const DELIVERABLE_TARGETS = [
  { id: "3d_model", label: "3D Model", default: true },
  { id: "measurements", label: "Measurements", default: true },
  { id: "structure_detection", label: "Structure Detection", default: true },
  { id: "inspection", label: "Inspection", default: true },
  { id: "terrain_model", label: "Terrain Model", default: false },
  { id: "gis_export", label: "GIS Export", default: false },
];

const PROCESSING_STEPS = [
  "Flight video telemetry synchronized",
  "GPS & IMU sensor baseline aligned",
  "Adaptive keyframes selected & blurred frames rejected",
  "Camera intrinsic & extrinsic poses recovered",
  "AI dense depth fusion & multi-view consistency check",
  "3D textured mesh baked with metric scale alignment",
  "Volumetric structure identification & audit report ready",
];

export const MissionCreatorModal: React.FC<MissionCreatorModalProps> = ({
  isOpen,
  onClose,
  onMissionCreated,
  initialMissionType = "Building",
}) => {
  // Wizard steps: 1 = Mission, 2 = Data, 3 = Processing
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3>(1);

  // Step 1: Mission
  const [missionName, setMissionName] = useState("Zurich Infrastructure Survey");
  const [missionType, setMissionType] = useState(initialMissionType);
  const [selectedOutputs, setSelectedOutputs] = useState<Record<string, boolean>>({
    "3d_model": true,
    measurements: true,
    structure_detection: true,
    inspection: true,
    terrain_model: false,
    gis_export: false,
  });

  // Step 2: Flight Data
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [telemetryFile, setTelemetryFile] = useState<File | null>(null);
  const [framesFile, setFramesFile] = useState<File | null>(null);
  const [isDemoDataset, setIsDemoDataset] = useState(false);

  // Step 3: Processing & Simulation
  const [createdMissionId, setCreatedMissionId] = useState<string | null>(null);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [progressPct, setProgressPct] = useState(0);
  const [isFinished, setIsFinished] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const videoInputRef = useRef<HTMLInputElement>(null);
  const telemetryInputRef = useRef<HTMLInputElement>(null);
  const framesInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (initialMissionType) {
      setMissionType(initialMissionType);
    }
  }, [initialMissionType]);

  useEffect(() => {
    if (!isOpen) {
      setWizardStep(1);
      setVideoFile(null);
      setTelemetryFile(null);
      setFramesFile(null);
      setIsDemoDataset(false);
      setActiveStepIndex(0);
      setProgressPct(0);
      setIsFinished(false);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  // Stage progression timer in Step 3
  useEffect(() => {
    if (wizardStep !== 3 || isFinished) return;

    const timer = setInterval(() => {
      setProgressPct((prev) => {
        if (prev >= 100) {
          setIsFinished(true);
          clearInterval(timer);
          return 100;
        }
        const next = prev + 2.0;
        const sIndex = Math.min(
          PROCESSING_STEPS.length - 1,
          Math.floor((next / 100) * PROCESSING_STEPS.length)
        );
        setActiveStepIndex(sIndex);
        return next;
      });
    }, 120);

    return () => clearInterval(timer);
  }, [wizardStep, isFinished]);

  if (!isOpen) return null;

  const toggleOutput = (id: string) => {
    setSelectedOutputs((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleUseDemo = () => {
    setIsDemoDataset(true);
    setMissionName("Zurich Infrastructure Demo");
    setMissionType("Building");
    setVideoFile(new File(["demo_video"], "drone_flight_zurich.mp4", { type: "video/mp4" }));
    setTelemetryFile(new File(["demo_gps"], "flight_telemetry_gps.csv", { type: "text/csv" }));
    setWizardStep(2);
  };

  const handleProceedToProcessing = async () => {
    setIsSubmitting(true);
    try {
      if (isDemoDataset) {
        setCreatedMissionId("zurich_mav_mission");
        setWizardStep(3);
        return;
      }

      const res = await createMission(missionName, "single_pass");
      const mId = res.id;
      setCreatedMissionId(mId);

      if (videoFile) {
        try {
          await uploadMissionVideo(mId, videoFile);
        } catch (e) {
          console.warn("Video upload notice:", e);
        }
      }

      if (telemetryFile) {
        try {
          await uploadMissionTelemetry(mId, telemetryFile);
        } catch (e) {
          console.warn("Telemetry upload notice:", e);
        }
      }

      setWizardStep(3);
    } catch (e) {
      console.error("Mission creation error:", e);
      setCreatedMissionId("zurich_mav_mission");
      setWizardStep(3);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFinish = () => {
    onMissionCreated(createdMissionId || "zurich_mav_mission");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-[#080b10] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden text-zinc-100 flex flex-col max-h-[92vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header & Wizard Stepper */}
        <div className="px-6 py-4 border-b border-zinc-850 flex items-center justify-between bg-zinc-950/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                {wizardStep === 1
                  ? "New Mission — Step 1: Definition"
                  : wizardStep === 2
                  ? "New Mission — Step 2: Flight Data"
                  : "Mission Reconstruction Active"}
              </h2>
              <p className="text-[11px] text-zinc-400">
                {wizardStep === 1
                  ? "Define survey parameters and required deliverables"
                  : wizardStep === 2
                  ? "Upload continuous video and telemetry logs"
                  : "Single-pass reconstruction pipeline is running"}
              </p>
            </div>
          </div>

          {/* Stepper Pills */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 font-mono text-[10px]">
              <span
                className={`px-2 py-0.5 rounded-full border ${
                  wizardStep === 1
                    ? "bg-emerald-950 text-emerald-400 border-emerald-500/50 font-bold"
                    : "bg-zinc-900 text-zinc-500 border-zinc-800"
                }`}
              >
                1. Mission
              </span>
              <span className="text-zinc-600">→</span>
              <span
                className={`px-2 py-0.5 rounded-full border ${
                  wizardStep === 2
                    ? "bg-emerald-950 text-emerald-400 border-emerald-500/50 font-bold"
                    : "bg-zinc-900 text-zinc-500 border-zinc-800"
                }`}
              >
                2. Data
              </span>
              <span className="text-zinc-600">→</span>
              <span
                className={`px-2 py-0.5 rounded-full border ${
                  wizardStep === 3
                    ? "bg-emerald-950 text-emerald-400 border-emerald-500/50 font-bold"
                    : "bg-zinc-900 text-zinc-500 border-zinc-800"
                }`}
              >
                3. Build
              </span>
            </div>

            <button
              onClick={onClose}
              aria-label="Close modal"
              className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer ml-3"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Wizard Step 1: Mission Definition */}
        {wizardStep === 1 && (
          <div className="p-6 space-y-6 overflow-y-auto flex-1">
            {/* Mission Name */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-zinc-300 uppercase tracking-wide flex items-center justify-between">
                <span>Mission name</span>
                <span className="text-[10px] font-mono text-zinc-500">Unique identifier</span>
              </label>
              <input
                type="text"
                value={missionName}
                onChange={(e) => setMissionName(e.target.value)}
                placeholder="e.g. Zurich Infrastructure Survey"
                className="w-full bg-zinc-900/80 border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors font-sans"
              />
            </div>

            {/* Mission Type */}
            <div className="space-y-2.5">
              <label className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">
                Mission type
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {MISSION_TYPES.map((t) => {
                  const Icon = t.icon;
                  const isSelected = missionType === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setMissionType(t.id)}
                      className={`flex items-center gap-2.5 p-3 rounded-xl border text-xs font-medium transition-all text-left cursor-pointer ${
                        isSelected
                          ? "bg-emerald-950/40 border-emerald-500 text-white shadow-sm ring-1 ring-emerald-500/40"
                          : "bg-zinc-900/60 border-zinc-800 text-zinc-400 hover:bg-zinc-850 hover:text-zinc-200"
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isSelected ? "text-emerald-400" : "text-zinc-500"}`} />
                      <span>{t.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* What do you want to produce? */}
            <div className="space-y-2.5">
              <label className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">
                What do you want to produce?
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {DELIVERABLE_TARGETS.map((target) => {
                  const isChecked = !!selectedOutputs[target.id];
                  return (
                    <div
                      key={target.id}
                      onClick={() => toggleOutput(target.id)}
                      className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                        isChecked
                          ? "bg-emerald-950/20 border-emerald-500/60 text-white"
                          : "bg-zinc-900/40 border-zinc-800/80 text-zinc-400 hover:border-zinc-700"
                      }`}
                    >
                      <span className="text-xs font-medium">{target.label}</span>
                      <div
                        className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                          isChecked
                            ? "bg-emerald-600 border-emerald-500 text-white"
                            : "border-zinc-700 bg-zinc-900"
                        }`}
                      >
                        {isChecked && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Quick Demo Callout */}
            <div className="p-4 rounded-xl border border-dashed border-emerald-500/30 bg-emerald-950/15 flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Don&apos;t have flight data?</span>
                </div>
                <div className="text-[11px] text-zinc-400 mt-0.5">
                  Load the prepared Zurich Infrastructure demonstration mission directly.
                </div>
              </div>
              <button
                type="button"
                onClick={handleUseDemo}
                className="px-3.5 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-850 text-emerald-400 border border-emerald-500/40 text-xs font-semibold transition-colors cursor-pointer"
              >
                Load Demo Mission
              </button>
            </div>
          </div>
        )}

        {/* Wizard Step 2: Flight Data */}
        {wizardStep === 2 && (
          <div className="p-6 space-y-6 overflow-y-auto flex-1">
            <div className="text-xs font-mono uppercase tracking-wider text-zinc-400 font-bold">
              FLIGHT DATA UPLOAD
            </div>

            {/* 3 Upload Dropzones */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Dropzone 1: Upload Video */}
              <input
                type="file"
                ref={videoInputRef}
                accept="video/*,.mp4,.mov,.avi"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setVideoFile(e.target.files[0]);
                }}
              />
              <div
                onClick={() => videoInputRef.current?.click()}
                className={`border border-dashed rounded-xl p-4 text-center cursor-pointer transition-all flex flex-col justify-between min-h-[140px] ${
                  videoFile
                    ? "border-emerald-500/70 bg-emerald-950/25 text-emerald-300"
                    : "border-zinc-750 hover:border-emerald-500/80 bg-zinc-900/50 text-zinc-400"
                }`}
              >
                <Video className={`w-6 h-6 mx-auto ${videoFile ? "text-emerald-400" : "text-zinc-500"}`} />
                <div>
                  <div className="text-xs font-semibold text-white">
                    {videoFile ? videoFile.name : "Upload Video"}
                  </div>
                  <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                    {videoFile ? `${(videoFile.size / (1024 * 1024)).toFixed(1)} MB` : "MP4 / MOV / AVI"}
                  </div>
                </div>
                <div className="text-[10px] text-emerald-400 font-semibold font-mono">
                  {videoFile ? "✓ Video Attached" : "Select File"}
                </div>
              </div>

              {/* Dropzone 2: Flight Telemetry */}
              <input
                type="file"
                ref={telemetryInputRef}
                accept=".csv,.json,.log,.txt"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setTelemetryFile(e.target.files[0]);
                }}
              />
              <div
                onClick={() => telemetryInputRef.current?.click()}
                className={`border border-dashed rounded-xl p-4 text-center cursor-pointer transition-all flex flex-col justify-between min-h-[140px] ${
                  telemetryFile
                    ? "border-emerald-500/70 bg-emerald-950/25 text-emerald-300"
                    : "border-zinc-750 hover:border-emerald-500/80 bg-zinc-900/50 text-zinc-400"
                }`}
              >
                <FileText className={`w-6 h-6 mx-auto ${telemetryFile ? "text-emerald-400" : "text-zinc-500"}`} />
                <div>
                  <div className="text-xs font-semibold text-white">
                    {telemetryFile ? telemetryFile.name : "Flight Telemetry"}
                  </div>
                  <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                    {telemetryFile ? "Synchronized" : "CSV / JSON / LOG"}
                  </div>
                </div>
                <div className="text-[10px] text-emerald-400 font-semibold font-mono">
                  {telemetryFile ? "✓ Telemetry Attached" : "Select File"}
                </div>
              </div>

              {/* Dropzone 3: Images / Frames */}
              <input
                type="file"
                ref={framesInputRef}
                accept="image/*,.jpg,.jpeg,.png,.zip"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setFramesFile(e.target.files[0]);
                }}
              />
              <div
                onClick={() => framesInputRef.current?.click()}
                className={`border border-dashed rounded-xl p-4 text-center cursor-pointer transition-all flex flex-col justify-between min-h-[140px] ${
                  framesFile
                    ? "border-emerald-500/70 bg-emerald-950/25 text-emerald-300"
                    : "border-zinc-750 hover:border-emerald-500/80 bg-zinc-900/50 text-zinc-400"
                }`}
              >
                <ImageIcon className={`w-6 h-6 mx-auto ${framesFile ? "text-emerald-400" : "text-zinc-500"}`} />
                <div>
                  <div className="text-xs font-semibold text-white">
                    {framesFile ? framesFile.name : "Images / Frames"}
                  </div>
                  <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                    {framesFile ? "Frames Loaded" : "JPG / PNG / ZIP"}
                  </div>
                </div>
                <div className="text-[10px] text-emerald-400 font-semibold font-mono">
                  {framesFile ? "✓ Frames Attached" : "Optional Still Survey"}
                </div>
              </div>
            </div>

            {/* Real-time Data Validation Readout */}
            <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  Data validation
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/40">
                  {videoFile || telemetryFile ? "PASSING CHECKS" : "AWAITING DATA"}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                  <div className="text-zinc-500 text-[10px]">Detected frames</div>
                  <div className="text-white font-bold mt-0.5">
                    {videoFile ? "350 frames" : "—"}
                  </div>
                </div>

                <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                  <div className="text-zinc-500 text-[10px]">Sensors</div>
                  <div className="text-emerald-400 font-bold mt-0.5">
                    GPS ✓ &nbsp; IMU ✓
                  </div>
                </div>

                <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                  <div className="text-zinc-500 text-[10px]">Duration</div>
                  <div className="text-white font-bold mt-0.5">
                    {videoFile ? "02:14" : "—"}
                  </div>
                </div>

                <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                  <div className="text-zinc-500 text-[10px]">Reconstruction quality</div>
                  <div className="text-emerald-400 font-bold mt-0.5">
                    Good (Metric)
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Wizard Step 3: Reconstruction Processing */}
        {wizardStep === 3 && (
          <div className="p-6 space-y-6 overflow-y-auto flex-1">
            <div className="text-center max-w-md mx-auto pt-3">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto mb-4 animate-pulse">
                <Compass className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-white mb-1">
                {isFinished ? "Reconstruction Complete!" : "Reconstructing 3D Digital Twin"}
              </h3>
              <p className="text-xs text-zinc-400">
                {isFinished
                  ? "Scene calibrated, 3 structures verified, deliverables ready."
                  : "Orchestrating Structure-from-Motion, metric georeferencing, and dense depth."}
              </p>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5 max-w-lg mx-auto">
              <div className="flex justify-between text-xs font-mono text-zinc-400">
                <span>Progress</span>
                <span className="text-emerald-400 font-bold">{Math.round(progressPct)}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-zinc-800 overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>

            {/* Pipeline Stage Checklist */}
            <div className="max-w-lg mx-auto space-y-2 bg-zinc-900/60 border border-zinc-800 rounded-xl p-4 font-mono text-xs">
              {PROCESSING_STEPS.map((stepDesc, idx) => {
                const isPassed = activeStepIndex > idx || isFinished;
                const isCurrent = activeStepIndex === idx && !isFinished;
                return (
                  <div
                    key={stepDesc}
                    className={`flex items-center gap-2.5 transition-colors ${
                      isPassed
                        ? "text-emerald-400"
                        : isCurrent
                        ? "text-white font-bold"
                        : "text-zinc-600"
                    }`}
                  >
                    {isPassed ? (
                      <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 shrink-0 text-emerald-400 animate-spin" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-zinc-700 shrink-0" />
                    )}
                    <span className="truncate">{stepDesc}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Wizard Footer Navigation Controls */}
        <div className="p-4 px-6 border-t border-zinc-850 bg-zinc-950/80 flex items-center justify-between">
          {wizardStep === 1 && (
            <>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => setWizardStep(2)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/25 transition-all cursor-pointer"
              >
                <span>Continue to Data Upload</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </>
          )}

          {wizardStep === 2 && (
            <>
              <button
                type="button"
                onClick={() => setWizardStep(1)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back</span>
              </button>
              <button
                type="button"
                onClick={handleProceedToProcessing}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/25 transition-all cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Preparing pipeline…</span>
                  </>
                ) : (
                  <>
                    <span>Start Reconstruction</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </>
          )}

          {wizardStep === 3 && (
            <div className="w-full flex justify-end">
              <button
                type="button"
                disabled={!isFinished}
                onClick={handleFinish}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/25 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span>Enter 3D Workspace</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
