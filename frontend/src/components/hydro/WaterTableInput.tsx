'use client';

import { useAnalysisStore } from '@/store/analysisStore';

export default function WaterTableInput() {
  const elevation = useAnalysisStore((s) => s.waterTable.elevation);
  const setWaterTable = useAnalysisStore((s) => s.setWaterTable);

  return (
    <section className="tool-panel">
      <div className="section-heading">
        <h2><span className="step-badge">3</span>Nappe phréatique</h2>
        <span>Hydraulique</span>
      </div>
      <label className="grid gap-1 text-xs font-semibold text-slate-600" htmlFor="water-table-elevation">
        Niveau z (m)
        <input
          id="water-table-elevation"
          type="number"
          step={0.1}
          value={elevation}
          onChange={(e) =>
            setWaterTable({ elevation: parseFloat(e.target.value) })
          }
          className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
        />
      </label>
    </section>
  );
}
