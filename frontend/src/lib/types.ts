/**
 * TypeScript interfaces mirroring backend/app/schemas.py exactly.
 * Keep in sync whenever schemas.py changes.
 */

export interface TerrainPoint {
  x: number;
  y: number;
}

export interface SoilLayer {
  id: number;
  name: string;
  /** Unit weight γ in kN/m³ */
  gamma: number;
  /** Effective cohesion c' in kPa */
  cohesion: number;
  /** Effective friction angle φ' in degrees */
  phi_deg: number;
  /** Layer thickness in metres; null for substratum */
  thickness: number | null;
}

export interface WaterTable {
  /** Piezometric elevation in metres */
  elevation: number | null;
}

export interface Circle {
  cx: number;
  cy: number;
  radius: number;
}

export interface Slice {
  index: number;
  // Geometry
  x_left: number;
  x_right: number;
  x_mid: number;
  width: number;
  y_top: number;
  y_base: number;
  height: number;
  area: number;
  // Base geometry
  alpha_deg: number;
  base_length: number;
  // Soil identity
  layer_id: number;
  cohesion: number;
  phi_deg: number;
  // Forces (kN/m)
  weight: number;
  pore_pressure: number;
  pore_force: number;
  // Spencer results
  normal_eff: number;
  driving: number;
  resisting: number;
}

export interface SpencerSettings {
  n_slices: number;
  tolerance: number;
  max_iter: number;
  theta_min: number;
  theta_max: number;
}

export interface CriticalSearchSettings {
  coarse_step: number;
  fine_step: number;
  final_step: number;
  top_k_coarse: number;
  top_k_fine: number;
  n_radii: number;
  min_convergence_ratio: number;
}

export interface AnalysisRequest {
  layers: SoilLayer[];
  water_table: WaterTable;
  circle: Circle;
  settings?: SpencerSettings;
  slope_height: number;
  slope_length: number;
}

export interface CriticalCircleRequest {
  layers: SoilLayer[];
  water_table: WaterTable;
  settings?: SpencerSettings;
  search?: CriticalSearchSettings;
  slope_height: number;
  slope_length: number;
}

export interface SearchStats {
  tested: number;
  converged: number;
  rejected: number;
}

export interface AnalysisResult {
  fs: number;
  stability_status: 'unstable' | 'limit' | 'stable';
  theta: number;
  slices: Slice[];
  converged: boolean;
  iterations: number;
  elapsed_seconds: number;
  circle: Circle;
}

export interface CriticalCircleResult {
  critical_circle: Circle;
  fs: number;
  result: AnalysisResult;
  stats: SearchStats;
}

export interface AppError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ErrorResponse {
  error: AppError;
}

export interface ValidationResponse {
  ok: boolean;
  errors: string[];
}

export type AnalysisStatus = 'idle' | 'loading' | 'error' | 'done';

// ---------------------------------------------------------------------------
// Cost estimation
// ---------------------------------------------------------------------------

export interface CostEstimate {
  n_candidates: number;
  n_slices: number;
  n_layers: number;
  max_iter: number;
  cost_score: number;
  /** 'light' | 'moderate' | 'heavy' | 'prohibitive' */
  level: string;
  recommended_mode: string;
  warnings: string[];
  estimated_seconds_min: number;
  estimated_seconds_max: number;
}

// ---------------------------------------------------------------------------
// Batch progress
// ---------------------------------------------------------------------------

export interface BatchProgress {
  batch_index: number;
  batches_total: number;
  tested_so_far: number;
  converged_so_far: number;
  rejected_so_far: number;
  best_fs_so_far: number | null;
  best_circle_so_far: Circle | null;
  elapsed_seconds: number;
  cancelled: boolean;
}

// ---------------------------------------------------------------------------
// Async job system
// ---------------------------------------------------------------------------

export type JobState = 'pending' | 'running' | 'done' | 'failed' | 'cancelled';

export interface JobStatus {
  job_id: string;
  state: JobState;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  progress: BatchProgress | null;
  result: CriticalCircleResult | null;
  error: { code: string; message: string; details: Record<string, unknown> } | null;
  request_summary: Record<string, unknown>;
}

export interface JobCreateResponse {
  job_id: string;
  state: JobState;
  cost_estimate: CostEstimate;
}

export type AnalysisMode = 'fast' | 'precise' | 'advanced';
