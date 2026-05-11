'use client';

import { useEffect, useState } from 'react';
import { useAnalysisStore } from '@/store/analysisStore';

function parseDecimalInput(value: string) {
  const normalized = value.replace(',', '.').trim();
  if (normalized === '') return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export default function WaterTableInput() {
  const elevation = useAnalysisStore((s) => s.waterTable.elevation);
  const slopeHeight = useAnalysisStore((s) => s.slopeHeight);
  const setWaterTable = useAnalysisStore((s) => s.setWaterTable);
  const enabled = elevation !== null;
  const [draftElevation, setDraftElevation] = useState(elevation === null ? '0' : String(elevation));

  useEffect(() => {
    setDraftElevation(elevation === null ? '0' : String(elevation));
  }, [elevation]);

  const commitElevation = () => {
    const parsed = parseDecimalInput(draftElevation);
    if (parsed !== null) {
      setWaterTable({ elevation: parsed });
      setDraftElevation(String(parsed));
    }
  };
  const parsedElevation = parseDecimalInput(draftElevation);
  const elevationError = enabled && draftElevation.trim() === ''
    ? 'Valeur obligatoire lorsque la nappe est activée.'
    : enabled && parsedElevation === null
      ? 'Valeur numérique invalide.'
      : null;
  const elevationWarning = enabled && parsedElevation !== null && (
    parsedElevation < -slopeHeight || parsedElevation > 2 * slopeHeight
  )
    ? `Valeur éloignée du profil : utilisez de préférence entre ${(-slopeHeight).toFixed(1)} m et ${(2 * slopeHeight).toFixed(1)} m.`
    : null;

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
            type="text"
            inputMode="decimal"
            value={draftElevation}
            onChange={(e) => {
              const next = e.target.value;
              setDraftElevation(next);
              const parsed = parseDecimalInput(next);
              if (parsed !== null) setWaterTable({ elevation: parsed });
            }}
            onBlur={commitElevation}
            onKeyDown={(e) => {
              if (e.key === 'Enter') e.currentTarget.blur();
            }}
            className={`h-9 rounded-md border bg-white px-3 text-sm font-medium text-slate-900 outline-none transition focus:ring-2 ${
              elevationError
                ? 'border-red-300 focus:border-red-500 focus:ring-red-100'
                : elevationWarning
                  ? 'border-amber-300 focus:border-amber-500 focus:ring-amber-100'
                  : 'border-slate-300 focus:border-slate-500 focus:ring-slate-200'
            }`}
          />
          {elevationError && <span className="text-xs font-semibold text-red-600">{elevationError}</span>}
          {!elevationError && elevationWarning && <span className="text-xs font-semibold text-amber-700">{elevationWarning}</span>}
        </label>
      )}
    </section>
  );
}
