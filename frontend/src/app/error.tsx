'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[Spencer] Erreur non gérée :', error);
  }, [error]);

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
      <div className="w-full max-w-lg rounded-xl border border-red-200 bg-red-50 p-6 shadow">
        <p className="text-xs font-bold uppercase tracking-wide text-red-500">L'application a rencontré un problème</p>
        <h2 className="mt-1 text-xl font-black text-slate-950">Un affichage inattendu s'est produit</h2>
        <p className="mt-3 text-sm font-medium text-slate-700">
          {error.message
            ? error.message
            : 'L\'affichage a été interrompu. Cliquez sur "Réessayer" — vos données ne sont pas perdues.'}
        </p>
        <p className="mt-3 text-xs text-slate-400">
          Si le problème se reproduit, fermez et relancez l'application via 2_LANCER.bat.
        </p>
      </div>
      <button
        onClick={reset}
        className="h-10 rounded-lg bg-slate-950 px-6 text-sm font-bold text-white hover:bg-slate-800"
      >
        Réessayer
      </button>
    </div>
  );
}
