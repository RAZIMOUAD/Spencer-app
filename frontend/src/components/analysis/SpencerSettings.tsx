'use client';

import { useAnalysisStore } from '@/store/analysisStore';

interface FieldConfig {
  key: 'n_slices' | 'tolerance' | 'max_iter' | 'theta_min' | 'theta_max';
  label: string;
  unit?: string;
  step: number;
  min?: number;
  max?: number;
}

const FIELDS: FieldConfig[] = [
  {
    key: 'n_slices',
    label: 'Nombre de tranches',
    step: 1,
    min: 5,
    max: 200,
  },
  {
    key: 'tolerance',
    label: 'Tolérance de convergence',
    step: 1e-7,
    min: 1e-10,
  },
  {
    key: 'max_iter',
    label: 'Itérations max',
    step: 10,
    min: 10,
    max: 2000,
  },
  {
    key: 'theta_min',
    label: 'Angle θ min',
    unit: '°',
    step: 1,
    min: -89,
    max: 0,
  },
  {
    key: 'theta_max',
    label: 'Angle θ max',
    unit: '°',
    step: 1,
    min: 0,
    max: 89,
  },
];

export default function SpencerSettings() {
  const settings = useAnalysisStore((s) => s.settings);
  const setSettings = useAnalysisStore((s) => s.setSettings);

  return (
    <section className="tool-panel">
      <div className="section-heading">
        <h2><span className="step-badge">4</span>Paramètres Spencer</h2>
        <span>Solveur</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {FIELDS.map(({ key, label, unit, step, min, max }) => (
          <div key={key} className="flex flex-col gap-1">
            <label
              htmlFor={`spencer-${key}`}
              className="text-xs font-medium text-slate-600"
            >
              {label}
            </label>
            <div className="flex items-center gap-1">
              <input
                id={`spencer-${key}`}
                type="number"
                step={step}
                min={min}
                max={max}
                value={settings[key]}
                onChange={(e) =>
                  setSettings({ [key]: parseFloat(e.target.value) })
                }
                className="h-9 w-full rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
              />
              {unit && (
                <span className="text-xs text-slate-400">{unit}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
