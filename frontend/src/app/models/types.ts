export interface Manufacturer {
  id: string;
  name: string;
  country_code: string;
  website?: string;
  notes?: string;
}

export interface EngineCurvePoint {
  rpm: number;
  torque_nm: number;
  power_kw: number;
}

export interface Engine {
  id: string;
  engine_code: string;
  displacement_cc?: number;
  aspiration: string;
  max_power_kw: number;
  max_power_rpm?: number;
  max_torque_nm: number;
  max_torque_rpm?: number;
  max_rpm: number;
  idle_rpm: number;
  bsfc_g_kwh?: number;
  curve_points: EngineCurvePoint[];
}

export interface GearRatio {
  gear_number: number;
  ratio: number;
}

export interface Gearbox {
  id: string;
  gearbox_type: string;
  number_of_gears: number;
  final_drive_ratio: number;
  shift_time_ms: number;
  mechanical_efficiency: number;
  ratios: GearRatio[];
}

export interface Aerodynamics {
  drag_coefficient_cd: number;
  frontal_area_m2: number;
  cl?: number;
  front_downforce_fraction?: number;
}

export interface Suspension {
  weight_distribution_front: number;
  cg_height_m?: number;
  front_track_width_m?: number;
  rear_track_width_m?: number;
}

export interface TireSetup {
  tire_type: string;
  mu_peak_longitudinal: number;
  mu_peak_lateral: number;
  front_width_mm?: number;
  rear_width_mm?: number;
}

export interface Vehicle {
  id: string;
  manufacturer_id: string;
  manufacturer?: Manufacturer;
  model: string;
  generation?: string;
  variant: string;
  model_year: number;
  production_start_year?: number;
  production_end_year?: number;
  body_style?: string;
  market?: string;
  country_of_origin?: string;
  is_stock_specification?: boolean;
  mass_kg: number;
  mass_definition?: string;
  front_mass_fraction?: number;
  wheelbase_m?: number;
  front_track_m?: number;
  rear_track_m?: number;
  length_m?: number;
  width_m?: number;
  height_m?: number;
  ground_clearance_m?: number;
  seats?: number;
  doors?: number;
  fuel_tank_capacity_l?: number;
  pit_fuel_rate_l_s?: number;
  pit_tire_wear_threshold?: number;
  drive_type?: string; // RWD, FWD, AWD
  differential_type?: string;
  steering_type?: string;
  brake_front_type?: string;
  brake_rear_type?: string;
  abs?: boolean;
  stability_control?: boolean;
  source_url?: string;
  source_name?: string;
  data_confidence?: number;
  notes?: string;
  image_url?: string; // URL of vehicle image
  engine?: Engine;
  gearbox?: Gearbox;
  aerodynamics?: Aerodynamics;
  suspension?: Suspension;
  tire_setup?: TireSetup;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface TrackGeometryPoint {
  sequence_order: number;
  distance_from_start_m: number;
  curvature_k?: number;
  radius_m?: number;
  elevation_m?: number;
  slope_pct?: number;
  bank_angle_deg?: number;
  x_m?: number;
  y_m?: number;
}

export interface TrackVariant {
  id: string;
  track_id: string;
  name: string;
  length_m: number;
  is_closed_loop: boolean;
  number_of_turns?: number;
  sectors_count: number;
  points?: TrackGeometryPoint[];
}

export interface Track {
  id: string;
  name: string;
  track_type: string; // circuit, rally_stage, hillclimb, test_track
  country_code: string;
  city?: string;
  variants: TrackVariant[];
}

export interface ProfilePoint {
  s_m: number;
  speed_kmh: number;
  accel_x_g: number;
  accel_y_g: number;
  gear: number;
  rpm: number;
  throttle: number;
  brake: number;
}

/** Punto de perfil tal como lo devuelve el backend: distancia y valor. */
export interface ApiProfilePoint {
  d: number;
  v: number;
}

export interface SimulationResponse {
  simulation_run_id?: string;
  vehicle_id: string;
  vehicle_label: string;
  variant_id: string;
  model_version: string;
  total_time_s: number;
  sector_times_s: number[];
  max_speed_m_s: number;
  max_speed_kph: number;
  min_speed_m_s: number;
  min_speed_kph: number;
  avg_speed_m_s: number;
  avg_speed_kph: number;
  max_lateral_g: number;
  max_longitudinal_accel_g: number;
  max_braking_g: number;
  speed_profile: ApiProfilePoint[];
  gear_profile: ApiProfilePoint[];
  rpm_profile: ApiProfilePoint[];
  accel_profile: ApiProfilePoint[];
  radius_profile: ApiProfilePoint[];
  parameters: Record<string, unknown>;
  notes: string;
}

export interface CompareResultItem {
  vehicle_id: string;
  vehicle_label: string;
  total_time_s?: number;
  lap_time_formatted?: string;
  gap_s?: number;
  avg_speed_kph?: number;
  max_speed_kph?: number;
  min_speed_kph?: number;
  max_lateral_g?: number;
  rank?: number;
  error?: string;
  sector_times?: number[];
  profile?: ProfilePoint[];
}

export interface CompareResponse {
  variant_id: string;
  results: CompareResultItem[];
  fastest_vehicle_id?: string;
  time_gap_to_fastest_s?: (number | null)[];
  track_name?: string;
  variant_name?: string;
  track_length_m?: number;
}

export interface EnduranceRequest {
  vehicle_id: string;
  variant_id: string;
  race_duration_hours?: number;
  race_laps?: number;
  race_distance_km?: number;
  ambient_temp_c?: number;
  bsfc_g_kwh?: number;
  initial_fuel_l?: number;
  power_mode?: number;
  driver_aggression?: number;
  strategy?: {
    tank_capacity_l?: number;
    fuel_fill_rate_l_s?: number;
    tire_change_time_s?: number;
    brake_service_time_s?: number;
    pit_lane_delta_s?: number;
    min_fuel_reserve_l?: number;
    tire_wear_threshold?: number;
    brake_wear_threshold?: number;
    repair_on_pit?: boolean;
    force_pit_laps?: number[];
  };
  random_seed?: number;
}

export interface PitStopOutput {
  lap: number;
  race_time_s: number;
  duration_s: number;
  fuel_added_l: number;
  tyres_changed: boolean;
  brakes_serviced: boolean;
  repaired_components: string[];
  reason: string;
}

export interface FailureEventOutput {
  lap: number;
  race_time_s: number;
  component: string;
  cause: string;
  is_terminal: boolean;
}

export interface ComponentStatusOutput {
  name: string;
  wear_percent: number;
  final_temp_c: number;
  life_consumed_hours: number;
  total_life_consumed_hours?: number;
  services_count?: number;
  survival_probability: number;
  failed: boolean;
  degraded: boolean;
}

export interface LapTelemetrySummary {
  lap: number;
  lap_time_s: number;
  fuel_remaining_l: number;
  tyre_wear_percent: number;
  brake_wear_percent: number;
  engine_temp_c: number;
  tyre_temp_c: number;
  brakes_temp_c: number;
  pit_time_s: number;
}

export interface EnduranceResult {
  vehicle_id: string;
  variant_id: string;
  status: string;
  reason_dnf?: string;
  terminal_lap: number;
  total_laps_completed: number;
  total_distance_km: number;
  total_race_time_s: number;
  best_lap_time_s: number;
  average_lap_time_s: number;
  fuel_consumed_total_l: number;
  fuel_consumption_per_lap_l: number;
  fuel_remaining_l: number;
  total_pit_stops: number;
  total_time_in_pits_s: number;
  finish_probability: number;
  pit_stops: PitStopOutput[];
  failures: FailureEventOutput[];
  components: { [key: string]: ComponentStatusOutput };
  lap_history: LapTelemetrySummary[];
}
