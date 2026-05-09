'use client';

import { useAnalysisStore } from '@/store/analysisStore';
import LayerPanel from '@/components/layers/LayerPanel';
import SlopeCanvas from '@/components/geometry/SlopeCanvas';
import ResultsSummary from '@/components/results/ResultsSummary';
import WaterTableInput from '@/components/hydro/WaterTableInput';
import SpencerSettings from '@/components/analysis/SpencerSettings';

function NumberField({
  label,
  value,
  onChange,
  step = 0.5,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  step?: number;
}) {
  return (
    <label className="grid gap-1 text-xs font-semibold text-slate-600">
      <span>{label}</span>
      <input
        type="number"
        min={0.1}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
      />
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

  return (
    <section id="geometry" className="tool-panel scroll-mt-5">
      <StepHeader step="1" title="Géométrie" meta="Profil 2D" />
      <div className="grid grid-cols-2 gap-3">
        <NumberField label="Hauteur H (m)" value={slopeHeight} onChange={setSlopeHeight} />
        <NumberField label="Projection L (m)" value={slopeLength} onChange={setSlopeLength} />
      </div>
    </section>
  );
}

function SearchPanel() {
  const search = useAnalysisStore((s) => s.search);
  const setSearch = useAnalysisStore((s) => s.setSearch);
  const runCriticalAnalysis = useAnalysisStore((s) => s.runCriticalAnalysis);
  const status = useAnalysisStore((s) => s.status);

  const updateSearchField = (
    key: 'coarse_step' | 'fine_step' | 'final_step',
    value: number,
  ) => setSearch({ [key]: value });

  return (
    <section id="analysis" className="tool-panel scroll-mt-5">
      <StepHeader step="5" title="Calcul Spencer" meta="Cercle critique" />
      <div className="grid grid-cols-3 gap-2">
        {([
          ['coarse_step', 'Grossier'],
          ['fine_step', 'Fin'],
          ['final_step', 'Final'],
        ] as Array<['coarse_step' | 'fine_step' | 'final_step', string]>).map(([key, label]) => (
          <NumberField
            key={key}
            label={`${label} (m)`}
            value={search[key] as number}
            step={key === 'final_step' ? 0.01 : 0.1}
            onChange={(value) => updateSearchField(key, value)}
          />
        ))}
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
          <SpencerSettings />
          <SearchPanel />
        </div>
      </aside>

      <main id="model" className="flex min-h-0 flex-col gap-3 scroll-mt-5">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Étape 3 - Aperçu du modèle
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
