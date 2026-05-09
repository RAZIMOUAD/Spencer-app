'use client';

import Link from 'next/link';
import { useAnalysisStore } from '@/store/analysisStore';

const sections = [
  { id: 'geometry', href: '/#geometry', label: 'Géométrie' },
  { id: 'layers', href: '/#layers', label: 'Couches de sol' },
  { id: 'water-table', href: '/#water-table', label: 'Nappe phréatique' },
  { id: 'spencer-analysis', href: '/#analysis', label: 'Analyse Spencer' },
  { id: 'results', href: '/#results', label: 'Résultats' },
];

const footerLinks = [
  { id: 'guide', href: '/guide', label: 'Guide projet' },
  { id: 'team', href: '/collaborateurs', label: 'Collaborateurs' },
];

const statusLabel: Record<string, string> = {
  idle:    'En attente',
  loading: 'Calcul…',
  error:   'Erreur',
  done:    'Terminé',
};

const statusColor: Record<string, string> = {
  idle:    'bg-slate-300',
  loading: 'bg-yellow-400 animate-pulse',
  error:   'bg-red-500',
  done:    'bg-green-500',
};

export default function Sidebar() {
  const status = useAnalysisStore((s) => s.status);

  return (
    <aside className="flex w-48 flex-col gap-2 border-r border-slate-200 bg-white px-3 py-5">
      <nav className="flex flex-col gap-1">
        {sections.map(({ id, href, label }) => (
          <Link
            key={id}
            href={href}
            className="rounded-md px-3 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950"
          >
            {label}
          </Link>
        ))}
      </nav>

      <div className="flex-1" />

      <nav className="flex flex-col gap-1">
        {footerLinks.map(({ id, href, label }) => (
          <Link
            key={id}
            href={href}
            className="rounded-md px-3 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950"
          >
            {label}
          </Link>
        ))}
      </nav>

      {/* Status indicator */}
      <div className="mt-auto flex items-center gap-2 px-3 py-2 rounded-md bg-white border border-slate-200">
        <span
          className={`inline-block w-2.5 h-2.5 rounded-full ${statusColor[status]}`}
        />
        <span className="text-xs text-slate-600">{statusLabel[status]}</span>
      </div>
    </aside>
  );
}
