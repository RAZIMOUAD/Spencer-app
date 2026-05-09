'use client';

import { useAnalysisStore } from '@/store/analysisStore';

export default function WaterTableInput() {
  const elevation = useAnalysisStore((s) => s.waterTable.elevation);
  const setWaterTable = useAnalysisStore((s) => s.setWaterTable);
  const enabled = elevation !== null;

  return (
    <section className="tool-panel">
      <div className="section-heading">
        <h2><span className="step-badge">3</span>Nappe phréatique</h2>
        <span>{enabled ? 'Activée' : 'Désactivée'}</span>
      </div>
      <button
        type="button"
        onClick={() => setWaterTable({ elevation: enabled ? null : 0 })}
        className={`flex h-11 w-full items-center justify-between rounded-lg border px-4 text-sm font-black transition ${
          enabled
            ? 'border-sky-300 bg-sky-50 text-sky-800'
            : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
        }`}
      >
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true">💧</span>
          Nappe phréatique
        </span>
        <span>{enabled ? 'ON' : 'OFF'}</span>
      </button>

      {enabled && (
        <label className="mt-3 grid gap-1 text-xs font-semibold text-slate-600" htmlFor="water-table-elevation">
          Niveau de la nappe z (m)
          <input
            id="water-table-elevation"
            type="number"
            step={0.1}
            value={elevation ?? 0}
            onChange={(e) =>
              { const v = parseFloat(e.target.value); if (isFinite(v)) setWaterTable({ elevation: v }); }
            }
            className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
          />
        </label>
      )}
    </section>
  );
}
