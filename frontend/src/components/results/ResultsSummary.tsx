'use client';

import { useAnalysisStore } from '@/store/analysisStore';

function fsTone(fs: number, status?: string) {
  const resolvedStatus = status ?? (Math.abs(fs - 1) <= 0.01 ? 'limit' : fs > 1 ? 'stable' : 'unstable');
  if (resolvedStatus === 'limit') return { label: 'État limite', color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' };
  if (resolvedStatus === 'stable') return { label: 'Stable', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' };
  return { label: 'Instable', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' };
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-2 last:border-0">
      <span className="text-sm font-medium text-slate-500">{label}</span>
      <span className="text-sm font-bold tabular-nums text-slate-950">{value}</span>
    </div>
  );
}

const DEBUG_RESULTS = process.env.NEXT_PUBLIC_DEBUG_MODE === 'true';

export default function ResultsSummary() {
  const { result, criticalResult, status, errors } = useAnalysisStore((s) => ({
    result: s.result,
    criticalResult: s.criticalResult,
    status: s.status,
    errors: s.errors,
  }));
  const runCriticalAnalysis = useAnalysisStore((s) => s.runCriticalAnalysis);

  if (status === 'idle') {
    return (
      <section className="tool-panel">
        <div className="section-heading">
          <h2>Résultats</h2>
          <span>En attente</span>
        </div>
        <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-5 text-sm font-medium text-slate-500">
          <ol className="list-decimal space-y-1 pl-4">
            <li>Saisissez la géométrie du talus.</li>
            <li>Définissez les couches de sol et la nappe.</li>
            <li>Lancez le calcul automatique.</li>
          </ol>
        </div>
        <button
          onClick={runCriticalAnalysis}
          className="mt-3 h-11 w-full rounded-lg bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800"
        >
          Calculer maintenant
        </button>
      </section>
    );
  }

  if (status === 'loading') {
    return (
      <section className="tool-panel">
        <div className="section-heading">
          <h2>Résultats</h2>
          <span>Calcul</span>
        </div>
        <div className="rounded-md bg-slate-50 p-5 text-sm font-semibold text-slate-600">
          Calcul automatique en cours...
        </div>
      </section>
    );
  }

  if (status === 'error') {
    return (
      <section className="tool-panel border-red-200 bg-red-50">
        <div className="section-heading">
          <h2>Erreur</h2>
          <span>Calcul</span>
        </div>
        <ul className="space-y-1 text-sm font-medium text-red-700">
          {errors.map((e, i) => <li key={i}>{e}</li>)}
        </ul>
      </section>
    );
  }

  if (!result || !isFinite(result.fs)) return null;

  const tone = fsTone(result.fs, result.stability_status);

  return (
    <div className="space-y-3">
      <section className={`rounded-md border ${tone.border} ${tone.bg} p-5`}>
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Facteur de sécurité</p>
        <div className="mt-2 flex items-end justify-between gap-3">
          <p className={`text-6xl font-black leading-none tabular-nums ${tone.color}`}>
            {result.fs.toFixed(3)}
          </p>
          <span className={`rounded-md bg-white px-3 py-1 text-sm font-bold ${tone.color}`}>
            {tone.label}
          </span>
        </div>
      </section>

      {criticalResult && (
        <>
          <section className="tool-panel">
            <div className="section-heading">
              <h2>Cercle critique</h2>
              <span>Géométrie</span>
            </div>
            <Metric
              label="Centre"
              value={`(${criticalResult.critical_circle.cx.toFixed(2)}, ${criticalResult.critical_circle.cy.toFixed(2)})`}
            />
            <Metric label="Rayon" value={`${criticalResult.critical_circle.radius.toFixed(2)} m`} />
          </section>

          {DEBUG_RESULTS && (
            <>
              <section className="tool-panel">
                <div className="section-heading">
                  <h2>Debug calcul</h2>
                  <span>Développeur</span>
                </div>
                <Metric label="Angle θ" value={isFinite(result.theta) ? `${result.theta.toFixed(2)}°` : '—'} />
                <Metric label="Tranches" value={`${result.slices?.length ?? '—'}`} />
                <Metric label="Itérations" value={`${result.iterations ?? '—'}`} />
                <Metric label="Convergence" value={result.converged ? 'Oui' : 'Non'} />
              </section>

              <section className="tool-panel">
                <div className="section-heading">
                  <h2>Debug recherche</h2>
                  <span>Grille</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="result-tile">
                    <strong>{criticalResult.stats.tested}</strong>
                    <span>testés</span>
                  </div>
                  <div className="result-tile text-emerald-700">
                    <strong>{criticalResult.stats.converged}</strong>
                    <span>convergés</span>
                  </div>
                  <div className="result-tile text-red-700">
                    <strong>{criticalResult.stats.rejected}</strong>
                    <span>rejetés</span>
                  </div>
                </div>
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}
