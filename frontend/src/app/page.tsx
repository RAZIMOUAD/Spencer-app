'use client';

import { useEffect, useState } from 'react';
import { useAnalysisStore } from '@/store/analysisStore';
import LayerPanel from '@/components/layers/LayerPanel';
import SlopeCanvas from '@/components/geometry/SlopeCanvas';
import ResultsSummary from '@/components/results/ResultsSummary';
import WaterTableInput from '@/components/hydro/WaterTableInput';

function parseDecimalInput(value: string) {
  const normalized = value.replace(',', '.').trim();
  if (normalized === '') return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function NumberField({
  label,
  value,
  onChange,
  error,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  error?: string | null;
}) {
  const [draftValue, setDraftValue] = useState(String(value));

  useEffect(() => {
    setDraftValue(String(value));
  }, [value]);

  const commit = () => {
    const parsed = parseDecimalInput(draftValue);
    if (parsed !== null && parsed > 0) {
      onChange(parsed);
      setDraftValue(String(parsed));
      return;
    }
    setDraftValue(String(value));
  };

  return (
    <label className="grid gap-1 text-xs font-semibold text-slate-600">
      <span>{label}</span>
      <input
        type="text"
        inputMode="decimal"
        value={draftValue}
        onChange={(e) => {
          const next = e.target.value;
          setDraftValue(next);
          const parsed = parseDecimalInput(next);
          if (parsed !== null && parsed > 0) onChange(parsed);
        }}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur();
        }}
        className={`h-9 rounded-md border bg-white px-3 text-sm font-medium text-slate-900 outline-none transition focus:ring-2 ${
          error
            ? 'border-red-300 focus:border-red-500 focus:ring-red-100'
            : 'border-slate-300 focus:border-slate-500 focus:ring-slate-200'
        }`}
      />
      {error && <span className="text-xs font-semibold text-red-600">{error}</span>}
    </label>
  );
}

function StepHeader({
  step,
  title,
  meta,
}: {
  step: string;
  title: string;
  meta: string;
}) {
  return (
    <div className="section-heading">
      <h2><span className="step-badge">{step}</span>{title}</h2>
      <span>{meta}</span>
    </div>
  );
}

function GeometryPanel() {
  const slopeHeight = useAnalysisStore((s) => s.slopeHeight);
  const slopeLength = useAnalysisStore((s) => s.slopeLength);
  const setSlopeHeight = useAnalysisStore((s) => s.setSlopeHeight);
  const setSlopeLength = useAnalysisStore((s) => s.setSlopeLength);
  const ratio = slopeLength > 0 ? slopeHeight / slopeLength : Infinity;
  const heightError = slopeHeight <= 0 ? 'La hauteur doit être supérieure à 0 m.' : null;
  const lengthError = slopeLength <= 0 ? 'La projection doit être supérieure à 0 m.' : null;
  const ratioError = ratio > 10
    ? `Talus trop abrupt : H/L = ${ratio.toFixed(1)}. Maximum admis : 10.`
    : ratio < 0.05
      ? `Talus presque horizontal : H/L = ${ratio.toFixed(2)}. Augmentez H ou réduisez L.`
      : null;

  return (
    <section id="geometry" className="tool-panel scroll-mt-5">
      <StepHeader step="1" title="Géométrie" meta="Profil 2D" />
      <div className="grid grid-cols-2 gap-3">
        <NumberField label="Hauteur H (m)" value={slopeHeight} onChange={setSlopeHeight} error={heightError} />
        <NumberField label="Projection L (m)" value={slopeLength} onChange={setSlopeLength} error={lengthError} />
      </div>
      {ratioError && (
        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold leading-5 text-amber-800">
          {ratioError}
        </div>
      )}
    </section>
  );
}

function RunPanel() {
  const runCriticalAnalysis = useAnalysisStore((s) => s.runCriticalAnalysis);
  const status = useAnalysisStore((s) => s.status);

  return (
    <section id="analysis" className="tool-panel scroll-mt-5">
      <StepHeader step="4" title="Analyse automatique" meta="Cercle critique" />
      <div className="rounded-md bg-slate-50 p-3 text-sm font-medium leading-6 text-slate-600">
        Le logiciel gère automatiquement le calcul interne à partir des données
        physiques saisies, avec une recherche optimisée du cercle critique.
      </div>
      <button
        onClick={runCriticalAnalysis}
        disabled={status === 'loading'}
        className="mt-4 h-11 w-full rounded-lg bg-slate-950 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {status === 'loading' ? 'Calcul en cours...' : 'Calculer le cercle critique'}
      </button>
    </section>
  );
}

export default function HomePage() {
  const runCriticalAnalysis = useAnalysisStore((s) => s.runCriticalAnalysis);
  const status = useAnalysisStore((s) => s.status);

  return (
    <div className="grid h-full min-h-0 grid-cols-[420px_minmax(620px,1fr)_340px] gap-5">
      <aside className="min-h-0 overflow-y-auto pr-1">
        <div className="space-y-3">
          <GeometryPanel />
          <section id="layers" className="tool-panel scroll-mt-5">
            <StepHeader step="2" title="Couches de sol" meta="Paramètres c'-φ'" />
            <LayerPanel />
          </section>
          <div id="water-table" className="scroll-mt-5">
            <WaterTableInput />
          </div>
          <RunPanel />
        </div>
      </aside>

      <main id="model" className="flex min-h-0 flex-col gap-3 scroll-mt-5">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Étape 5 - Résultat graphique
            </p>
            <h1 className="text-xl font-bold text-slate-950">Profil du talus et surface de rupture</h1>
          </div>
          <button
            onClick={runCriticalAnalysis}
            disabled={status === 'loading'}
            className="h-10 rounded-lg bg-slate-950 px-5 text-sm font-bold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {status === 'loading' ? 'Calcul...' : 'Calculer'}
          </button>
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs font-bold text-slate-600">
          <div className="workflow-chip">1. Saisir le talus</div>
          <div className="workflow-chip">2. Vérifier les couches</div>
          <div className="workflow-chip">3. Lancer Spencer</div>
        </div>
        <SlopeCanvas />
      </main>

      <aside id="results" className="min-h-0 overflow-y-auto scroll-mt-5">
        <ResultsSummary />
      </aside>
    </div>
  );
}
