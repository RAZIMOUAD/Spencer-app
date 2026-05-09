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
    console.error('[Spencer] Erreur React non gérée :', error);
  }, [error]);

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
      <div className="w-full max-w-lg rounded-xl border border-red-200 bg-red-50 p-6 shadow">
        <p className="text-xs font-bold uppercase tracking-wide text-red-500">Erreur de l'application</p>
        <h2 className="mt-1 text-xl font-black text-slate-950">Un problème est survenu</h2>
        <p className="mt-3 text-sm font-medium text-slate-700">
          {error.message || 'Erreur inconnue. Vérifiez la console pour les détails.'}
        </p>
        {error.digest && (
          <p className="mt-2 font-mono text-xs text-slate-400">Digest : {error.digest}</p>
        )}
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
