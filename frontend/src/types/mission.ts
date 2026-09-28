export type GPSQualityTier =
  | "STRONG_GPS"
  | "WEAK_GPS"
  | "INSUFFICIENT_BASELINE"
  | "LOCAL_METRIC";

export interface SensorQualityReport {
  total_fixes: number;
  valid_fixes: number;
  horizontal_spread_m: number;
  vertical_spread_m: number;
  trajectory_baseline_m: number;
  estimated_noise_m: number;
  baseline_to_noise_ratio: number;
  quality_tier: GPSQualityTier;
  recommended_gps_weight: number;
  recommended_mode: string;
  has_imu: boolean;
  has_barometer: boolean;
  summary: string;
}

export type SemanticQualityTier =
  | "TRUSTED"
  | "REVIEW_RECOMMENDED"
  | "LOW_CONFIDENCE"
  | "UNKNOWN";

export interface SemanticQualityReport {
  n_points: number;
  mean_semantic_confidence: number | null;
  low_confidence_point_pct: number | null;
  oversized_instance_ids: number[];
  oversized_instance_count: number;
  max_plausible_footprint_m2: number;
  quality_tier: SemanticQualityTier;
  summary: string;
}

export interface BuildingInstance {
  instance_id: number;
  centroid_xyz: [number, number, number];
  footprint_area_m2: number;
  base_elevation_m: number;
  peak_elevation_m: number;
  height_m: number;
  volume_m3: number;
  point_count: number;
  mean_confidence: number;
  bounding_box_min: [number, number, number];
  bounding_box_max: [number, number, number];
}

export interface DeliverableFile {
  name: string;
  size_bytes: number;
  url: string;
}

export interface MissionSummary {
  id: string;
  name: string;
  category?: "MY_MISSIONS" | "DEMO_MISSIONS";
  is_demo?: boolean;
  mission_type?: string;
  has_deliverables: boolean;
  has_viewer_data: boolean;
  status: "COMPLETED" | "IN_PROGRESS" | "ARCHIVED" | "READY";
  total_frames?: number;
  registered_frames?: number;
  registration_rate_pct?: number;
  sparse_points?: number;
  telemetry_provenance?: string;
  georeferenced?: boolean;
  building_count?: number;
  sensor_quality?: SensorQualityReport;
  semantic_quality?: SemanticQualityReport;
  volumetric_metrics?: Record<string, unknown>;
}

export interface MissionDetail {
  id: string;
  report: {
    dataset: string;
    telemetry_provenance: string;
    georeferenced: boolean;
    total_input_frames: number;
    registered_frames: number;
    registration_rate_pct: number;
    sparse_points: number;
    scale_factor: number | null;
    mean_gps_residual_m: number | null;
    mean_reprojection_error_px: number;
    high_confidence_points_pct: number;
    sensor_quality?: SensorQualityReport;
    semantic_quality?: SemanticQualityReport;
    building_instances?: BuildingInstance[];
    georeference_origin?: {
      lat: number;
      lon: number;
      alt_m: number;
      epsg: number | null;
    };
    class_breakdown?: Array<{
      class_name: string;
      n_points: number;
      pct_high: number;
      pct_medium: number;
      pct_low: number;
      mean_track_len: number;
      mean_reprojection_error_px: number;
    }>;
  };
  deliverables: DeliverableFile[];
}

export interface TrajectoryPoint {
  frame: string;
  lat: number;
  lon: number;
  alt: number;
}

export interface MissionTrajectory {
  origin?: { lat: number; lon: number; alt: number };
  n_frames?: number;
  trajectory: TrajectoryPoint[];
}

