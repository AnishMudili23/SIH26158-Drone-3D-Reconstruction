import {
  MissionSummary,
  MissionDetail,
  BuildingInstance,
} from "@/types/mission";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// The backend is the only source of mission data. If it's unreachable, callers
// must surface that as an offline state — never substitute canned mission data,
// even real numbers from a past run, as if it were the live result of this request.

export async function fetchHealth(): Promise<{ status: string; gpu_available: boolean; device: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { next: { revalidate: 10 } });
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
