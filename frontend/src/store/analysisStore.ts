/**
 * Zustand store for global Spencer analysis state.
 */

import { create } from 'zustand';
import {
  runAnalysis as apiRunAnalysis,
  runCriticalCircle as apiRunCriticalCircle,
} from '@/lib/api';
import type {
  AnalysisResult,
  AnalysisStatus,
  Circle,
  CriticalCircleResult,
  CriticalSearchSettings,
  SoilLayer,
  SpencerSettings,
  WaterTable,
} from '@/lib/types';

// ---------------------------------------------------------------------------
// Default values
// ---------------------------------------------------------------------------

const DEFAULT_SETTINGS: SpencerSettings = {
  n_slices: 20,
  tolerance: 1e-6,
  max_iter: 200,
  theta_min: -30.0,
  theta_max: 30.0,
};

const DEFAULT_WATER_TABLE: WaterTable = { elevation: 0.0 };

const DEFAULT_CIRCLE: Circle = { cx: 0.0, cy: 20.0, radius: 15.0 };

const DEFAULT_SEARCH: CriticalSearchSettings = {
  coarse_step: 3.0,
  fine_step: 1.0,
  final_step: 0.5,
  top_k_coarse: 5,
  top_k_fine: 3,
  n_radii: 5,
  min_convergence_ratio: 0.05,
};

const DEFAULT_LAYERS: SoilLayer[] = [
  {
    id: 1,
    name: 'C1',
    gamma: 19.0,
    cohesion: 15.0,
    phi_deg: 25.0,
    thickness: null,
  },
];

// ---------------------------------------------------------------------------
// Store shape
// ---------------------------------------------------------------------------

interface AnalysisState {
  // --- domain data ---
  layers: SoilLayer[];
  waterTable: WaterTable;
  circle: Circle;
  settings: SpencerSettings;
  search: CriticalSearchSettings;
  slopeHeight: number;
  slopeLength: number;

  // --- async state ---
  result: AnalysisResult | null;
  criticalResult: CriticalCircleResult | null;
  status: AnalysisStatus;
  errors: string[];

  // --- actions ---
  setLayers: (layers: SoilLayer[]) => void;
  setWaterTable: (wt: WaterTable) => void;
  setCircle: (circle: Circle) => void;
  setSettings: (settings: Partial<SpencerSettings>) => void;
  setSearch: (settings: Partial<CriticalSearchSettings>) => void;
  setSlopeHeight: (h: number) => void;
  setSlopeLength: (l: number) => void;
  runAnalysis: () => Promise<void>;
  runCriticalAnalysis: () => Promise<void>;
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Store implementation
// ---------------------------------------------------------------------------

export const useAnalysisStore = create<AnalysisState>((set, get) => ({
  // --- initial state ---
  layers: DEFAULT_LAYERS,
  waterTable: DEFAULT_WATER_TABLE,
  circle: DEFAULT_CIRCLE,
  settings: DEFAULT_SETTINGS,
  search: DEFAULT_SEARCH,
  slopeHeight: 10.0,
  slopeLength: 15.0,
  result: null,
  criticalResult: null,
  status: 'idle',
  errors: [],

  // --- setters ---
  setLayers: (layers) => set({ layers }),
  setWaterTable: (waterTable) => set({ waterTable }),
  setCircle: (circle) => set({ circle }),
  setSettings: (partial) =>
    set((state) => ({ settings: { ...state.settings, ...partial } })),
  setSearch: (partial) =>
    set((state) => ({ search: { ...state.search, ...partial } })),
  setSlopeHeight: (slopeHeight) => set({ slopeHeight }),
  setSlopeLength: (slopeLength) => set({ slopeLength }),

  // --- async analysis ---
  runAnalysis: async () => {
    const state = get();
    set({ status: 'loading', errors: [], result: null, criticalResult: null });

    try {
      const result = await apiRunAnalysis({
        layers: state.layers,
        water_table: state.waterTable,
        circle: state.circle,
        settings: state.settings,
        slope_height: state.slopeHeight,
        slope_length: state.slopeLength,
      });
      set({ result, criticalResult: null, status: 'done' });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Erreur inconnue';
      set({ status: 'error', errors: [message] });
    }
  },

  runCriticalAnalysis: async () => {
    const state = get();
    set({ status: 'loading', errors: [], result: null, criticalResult: null });

    try {
      const criticalResult = await apiRunCriticalCircle({
        layers: state.layers,
        water_table: state.waterTable,
        settings: state.settings,
        search: state.search,
        slope_height: state.slopeHeight,
        slope_length: state.slopeLength,
      });
      set({
        result: criticalResult.result,
        criticalResult,
        circle: criticalResult.critical_circle,
        status: 'done',
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Erreur inconnue';
      set({ status: 'error', errors: [message] });
    }
  },

  // --- reset ---
  reset: () =>
    set({
      layers: DEFAULT_LAYERS,
      waterTable: DEFAULT_WATER_TABLE,
      circle: DEFAULT_CIRCLE,
      settings: DEFAULT_SETTINGS,
      search: DEFAULT_SEARCH,
      slopeHeight: 10.0,
      slopeLength: 15.0,
      result: null,
      criticalResult: null,
      status: 'idle',
      errors: [],
    }),
}));
