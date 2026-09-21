"use client";

import React from "react";
import { Check, X, AlertTriangle, HelpCircle } from "lucide-react";
import { MissionSummary } from "@/types/mission";

interface StatusStripProps {
  mission?: MissionSummary;
}

type ItemState = "ok" | "warn" | "off" | "unknown";

const STATE_STYLE: Record<ItemState, string> = {
  ok: "text-emerald-400",
  warn: "text-amber-400",
  off: "text-zinc-600",
  unknown: "text-zinc-600",
};

const STATE_ICON: Record<ItemState, React.ReactNode> = {
  ok: <Check className="w-3 h-3" />,
  warn: <AlertTriangle className="w-3 h-3" />,
  off: <X className="w-3 h-3" />,
  unknown: <HelpCircle className="w-3 h-3" />,
};

function Item({ label, state, detail }: { label: string; state: ItemState; detail?: string }) {
  return (
    <span
      title={detail}
      className={`inline-flex items-center gap-1 font-mono text-[10px] ${STATE_STYLE[state]}`}
    >
      {STATE_ICON[state]}
      {label}
    </span>
  );
}

// Every field here reads directly from the mission's actual report — nothing here
// is a static claim. If a signal wasn't computed for this mission, it shows as
// "unknown" rather than a guessed or default status.
export const StatusStrip: React.FC<StatusStripProps> = ({ mission }) => {
  if (!mission) {
    return (
      <div className="h-6 border-b border-zinc-800 bg-zinc-950/60 px-4 flex items-center text-[10px] font-mono text-zinc-600">
        No mission selected
      </div>
    );
  }

  const sq = mission.sensor_quality;
  const semq = mission.semantic_quality;

  const gpsState: ItemState =
    mission.telemetry_provenance === "REAL" ? "ok"
    : mission.telemetry_provenance === "SIMULATED" ? "warn"
    : mission.telemetry_provenance === "ESTIMATED" ? "warn"
    : "off";

  const imuState: ItemState = sq ? (sq.has_imu ? "ok" : "off") : "unknown";
  const baroState: ItemState = sq ? (sq.has_barometer ? "ok" : "off") : "unknown";

  const sfmState: ItemState =
    mission.registration_rate_pct == null ? "unknown"
    : mission.registration_rate_pct >= 95 ? "ok"
    : mission.registration_rate_pct > 0 ? "warn"
    : "off";

  const georefState: ItemState =
    !mission.georeferenced ? "off"
    : sq?.quality_tier === "STRONG_GPS" ? "ok"
    : sq?.quality_tier === "WEAK_GPS" || sq?.quality_tier === "INSUFFICIENT_BASELINE" ? "warn"
    : sq?.quality_tier === "LOCAL_METRIC" ? "off"
    : "unknown";

  const semanticState: ItemState =
    !semq ? "unknown"
    : semq.quality_tier === "TRUSTED" ? "ok"
    : semq.quality_tier === "UNKNOWN" ? "unknown"
    : "warn";

  return (
    <div className="h-6 border-b border-zinc-800 bg-zinc-950/60 px-4 flex items-center gap-4 overflow-x-auto">
      <Item
        label="GPS"
        state={gpsState}
        detail={`Telemetry provenance: ${mission.telemetry_provenance || "none"}`}
      />
      <Item
        label="IMU"
        state={imuState}
        detail={sq ? undefined : "Sensor quality not computed for this mission"}
      />
      <Item
        label="BARO"
        state={baroState}
        detail={sq ? undefined : "Sensor quality not computed for this mission"}
      />
      <Item
        label={`SfM ${mission.registration_rate_pct != null ? mission.registration_rate_pct.toFixed(0) + "%" : ""}`}
        state={sfmState}
      />
      <Item
        label="GEOREF"
        state={georefState}
        detail={sq?.summary}
      />
      <Item
        label="SEMANTIC"
        state={semanticState}
        detail={semq?.summary}
      />
    </div>
  );
};
