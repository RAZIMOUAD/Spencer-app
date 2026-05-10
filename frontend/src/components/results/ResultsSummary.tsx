'use client';

import { useEffect, useState } from 'react';
import { useAnalysisStore } from '@/store/analysisStore';
import type { BatchProgress } from '@/lib/types';

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

function ResultNotice() {
  return (
    <section className="rounded-md border border-slate-200 bg-white/70 p-4 text-xs leading-5 text-slate-500 shadow-sm">
      <p className="font-black uppercase tracking-wide text-slate-600">Repères rapides</p>
      <dl className="mt-2 space-y-1.5">
        <div><dt className="inline font-bold text-slate-700">FoS</dt><dd className="inline"> : facteur de sécurité du talus.</dd></div>
        <div><dt className="inline font-bold text-slate-700">Cercle critique</dt><dd className="inline"> : surface de rupture donnant le FoS minimal.</dd></div>
        <div><dt className="inline font-bold text-slate-700">Tranches</dt><dd className="inline"> : découpage vertical utilisé pour le calcul Spencer.</dd></div>
        <div><dt className="inline font-bold text-slate-700">Nappe</dt><dd className="inline"> : niveau d'eau qui génère les pressions interstitielles.</dd></div>
        <div><dt className="inline font-bold text-slate-700">Cercles analysés</dt><dd className="inline"> : candidats testés pour trouver le cercle critique.</dd></div>
        <div><dt className="inline font-bold text-slate-700">Itérations</dt><dd className="inline"> : étapes numériques nécessaires à la convergence du calcul final.</dd></div>
      </dl>
    </section>
  );
}

const PHASES = [
  { until: 15,  label: 'Analyse du talus' },
  { until: 45,  label: 'Exploration des surfaces de rupture' },
  { until: 90,  label: 'Affinement du cercle critique' },
  { until: Infinity, label: 'Calcul approfondi' },
];

function LoadingPanel({ progress }: { progress: BatchProgress | null }) {
  const [elapsed, setElapsed] = useState(0);
  const [dot, setDot] = useState(0);

  useEffect(() => {
    setElapsed(0);
    setDot(0);
    const clock = setInterval(() => setElapsed((s) => s + 1), 1000);
    const dots  = setInterval(() => setDot((d) => (d + 1) % 3), 500);
    return () => { clearInterval(clock); clearInterval(dots); };
  }, []);

  const displayElapsed = progress ? Math.round(progress.elapsed_seconds) : elapsed;
  const phase = PHASES.find((p) => displayElapsed < p.until)!;

  return (
    <section className="tool-panel overflow-hidden">
      {/* barre de progression indéterminée */}
      <div className="relative h-1 w-full overflow-hidden bg-slate-100">
        <div className="absolute inset-y-0 w-2/5 animate-[loading-bar_1.6s_ease-in-out_infinite] rounded-full bg-slate-600" />
      </div>

      <div className="section-heading mt-3">
        <h2>Résultats</h2>
        <span>Calcul Spencer</span>
      </div>

      <div className="rounded-md bg-slate-50 p-4 space-y-3">
        {/* texte + points animés */}
        <div className="flex items-center gap-2">
          <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-200 border-t-slate-600 shrink-0" />
          <span className="text-sm font-semibold text-slate-700">
            {phase.label}
            <span className="inline-flex gap-px ml-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="inline-block h-1 w-1 rounded-full bg-slate-500 transition-opacity duration-300"
                  style={{ opacity: dot >= i ? 1 : 0.2 }}
                />
              ))}
            </span>
          </span>
        </div>

        {/* jauge de phases */}
        <div className="flex gap-1">
          {PHASES.slice(0, 3).map((p, i) => {
            const phaseIdx = PHASES.indexOf(phase);
            const done  = i < phaseIdx;
            const active = i === phaseIdx;
            return (
              <div key={i} className="flex-1 h-1 rounded-full overflow-hidden bg-slate-200">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${
                    done ? 'w-full bg-slate-500' : active ? 'w-2/3 bg-slate-400 animate-pulse' : 'w-0'
                  }`}
                />
              </div>
            );
          })}
        </div>

        {/* compteur + données temps réel */}
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Temps écoulé</span>
          <span className="tabular-nums font-bold text-slate-700">{displayElapsed}s</span>
        </div>

        {progress && (
          <div className="grid grid-cols-3 gap-2 border-t border-slate-200 pt-3">
            <div className="result-tile">
              <strong className="text-slate-700 text-sm">{progress.tested_so_far.toLocaleString()}</strong>
              <span>cercles testés</span>
            </div>
            <div className="result-tile text-emerald-700">
              <strong className="text-sm">{progress.converged_so_far.toLocaleString()}</strong>
              <span>convergés</span>
            </div>
            <div className="result-tile text-slate-700">
              <strong className="text-sm">
                {progress.best_fs_so_far != null ? progress.best_fs_so_far.toFixed(3) : '—'}
              </strong>
              <span>FoS actuel</span>
            </div>
          </div>
        )}

        {displayElapsed >= 30 && (
          <p className="text-xs text-slate-400 leading-5 border-t border-slate-200 pt-3">
            Normal sur les grands talus — ne fermez pas cette fenêtre.
            Pour accélérer, augmentez les valeurs Grossier / Fin / Final (étape 4).
          </p>
        )}
      </div>
    </section>
  );
}

export default function ResultsSummary() {
  const { result, criticalResult, status, errors, progress } = useAnalysisStore((s) => ({
    result: s.result,
    criticalResult: s.criticalResult,
    status: s.status,
    errors: s.errors,
    progress: s.progress,
  }));
  const runCriticalAnalysis = useAnalysisStore((s) => s.runCriticalAnalysis);

  if (status === 'idle') {
    return (
      <div className="space-y-3">
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
        <ResultNotice />
      </div>
    );
  }

  if (status === 'loading') {
    return <LoadingPanel progress={progress} />;
  }

  if (status === 'error') {
    return (
      <section className="tool-panel border-red-200 bg-red-50">
        <div className="section-heading">
          <h2>Le calcul a échoué</h2>
          <span>À corriger</span>
        </div>
        <ul className="space-y-2 text-sm font-medium text-red-700">
          {errors.map((e, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-0.5 shrink-0">•</span>
              <span>{e}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-red-500">
          Corrigez les points ci-dessus et relancez le calcul.
        </p>
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
        {criticalResult && (
          <div className="mt-4 space-y-1 border-t border-white/70 pt-3 text-xs font-bold leading-5 text-slate-600">
            <p>Centre du cercle : xc = {criticalResult.critical_circle.cx.toFixed(2)} m | yc = {criticalResult.critical_circle.cy.toFixed(2)} m</p>
            <p>Rayon R : {criticalResult.critical_circle.radius.toFixed(2)} m</p>
            <p>Nombre de tranches : {result.slices?.length ?? '—'}</p>
            <p>Cercles analysés : {criticalResult.stats.tested}</p>
            <p>Itérations de calcul : {result.converged ? result.iterations : 'Échec de convergence'}</p>
            <p>Temps de calcul : {result.elapsed_seconds.toFixed(1)} s</p>
          </div>
        )}
      </section>

      <ResultNotice />

      {criticalResult && (
        <>
          {DEBUG_RESULTS && (
            <>
              <section className="tool-panel">
                <div className="section-heading">
                  <h2>Debug calcul</h2>
                  <span>Développeur</span>
                </div>
                <Metric label="Angle θ" value={isFinite(result.theta) ? `${result.theta.toFixed(2)}°` : '—'} />
                <Metric label="Tranches" value={`${result.slices?.length ?? '—'}`} />
                <Metric label="Temps" value={`${result.elapsed_seconds.toFixed(3)} s`} />
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
