import {
  MissionSummary,
  MissionDetail,
  BuildingInstance,
} from "@/types/mission";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// The backend is the only source of mission data. If it's unreachable, callers
// must surface that as an offline state — never substitute canned mission data,
// even real numbers from a past run, as if it were the live result of this request.

export async function fetchHealth(): Promise<{ status: string; gpu_available: boolean; device: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
    if (res.ok) return await res.json();
  } catch {
    // ignore
  }
  return { status: "offline", gpu_available: false, device: "unknown" };
}

export async function fetchMissions(): Promise<MissionSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/api/missions`, { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) return data;
    }
  } catch {
    // ignore
  }
  return [];
}

export async function fetchMissionDetail(missionId: string): Promise<MissionDetail | null> {
  try {
    const res = await fetch(`${API_BASE}/api/missions/${missionId}`, { cache: "no-store" });
    if (res.ok) return await res.json();
  } catch {
    // ignore
  }
  return null;
}

export async function fetchMissionBuildings(missionId: string): Promise<BuildingInstance[]> {
  try {
    const res = await fetch(`${API_BASE}/api/missions/${missionId}/buildings`, { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      return data.buildings || [];
    }
  } catch {
    // ignore
  }
  return [];
}

export async function fetchMissionTrajectory(missionId: string): Promise<import("@/types/mission").MissionTrajectory | null> {
  try {
    const res = await fetch(`${API_BASE}/api/missions/${missionId}/trajectory`, { cache: "no-store" });
    if (res.ok) return await res.json();
  } catch {
    // ignore
  }
  return null;
}

export async function createMission(name: string, mode: "single_pass" | "multi_view" = "single_pass"): Promise<any> {
  const res = await fetch(`${API_BASE}/api/missions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, mode }),
  });
  if (!res.ok) throw new Error(`Failed to create mission: ${res.statusText}`);
  return await res.json();
}

export async function uploadMissionVideo(missionId: string, file: File): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/upload/video`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Video upload failed: ${res.statusText}`);
  return await res.json();
}

export async function uploadMissionTelemetry(missionId: string, file: File): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/upload/telemetry`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Telemetry upload failed: ${res.statusText}`);
  return await res.json();
}

export async function analyzeMission(missionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/analyze`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`);
  return await res.json();
}

export async function startReconstruction(missionId: string, options?: any): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/reconstruct`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options || {}),
  });
  if (!res.ok) throw new Error(`Reconstruction failed to queue: ${res.statusText}`);
  return await res.json();
}

export async function fetchJobStatus(jobId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Job status check failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchMissionProvenance(missionId: string): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/api/missions/${missionId}/provenance`, { cache: "no-store" });
    if (res.ok) return await res.json();
  } catch {
    // ignore
  }
  return null;
}

export async function deleteMission(missionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete mission: ${res.statusText}`);
  return await res.json();
}

export async function clearDemoMissions(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/missions/clear-demo`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to clear demo missions: ${res.statusText}`);
  return await res.json();
}

export async function renameMission(missionId: string, name: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/rename`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Failed to rename mission: ${res.statusText}`);
  return await res.json();
}

export async function archiveMission(missionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/archive`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to archive mission: ${res.statusText}`);
  return await res.json();
}

export function getAssetDownloadUrl(missionId: string, assetType: string): string {
  return `${API_BASE}/api/missions/${missionId}/download/${assetType}`;
}

