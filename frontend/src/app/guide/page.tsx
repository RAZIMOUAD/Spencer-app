const faqs = [
  {
    title: 'Résumé du projet',
    tag: 'Vue globale',
    body: 'Ce projet consiste au développement d’une application de calcul de stabilité des talus basée sur la méthode de Spencer.',
    points: [
      'Définir la géométrie du talus',
      'Ajouter plusieurs couches de sol',
      'Activer une nappe phréatique',
      'Générer automatiquement des surfaces de rupture',
      'Calculer le facteur de sécurité du talus',
      'Rechercher automatiquement le cercle critique donnant le facteur de sécurité minimal',
    ],
  },
  {
    title: 'Pourquoi la méthode de Spencer ?',
    tag: 'Méthode',
    body: 'La méthode de Spencer est une méthode d’équilibre limite reconnue pour sa précision dans l’analyse de stabilité des talus. Elle satisfait simultanément l’équilibre des forces et l’équilibre des moments.',
    points: [
      'Méthode précise pour les ruptures circulaires',
      'Prise en compte des forces inter-tranches',
      'Vérification simultanée des forces et des moments',
      'Résultats fiables pour l’interprétation géotechnique',
    ],
  },
  {
    title: 'Que représentent les couches de calcul ?',
    tag: 'Sol',
    body: 'Les couches représentent les différentes formations géologiques du terrain. Ces paramètres influencent directement la stabilité du talus et le calcul du facteur de sécurité.',
    points: [
      'Poids volumique',
      'Cohésion',
      'Angle de frottement',
      'Épaisseur',
    ],
  },
  {
    title: 'Comment lire le facteur de sécurité ?',
    tag: 'Résultat',
    body: 'Le facteur de sécurité (FoS) représente le rapport entre les forces résistantes et les forces motrices du glissement. Plus le FoS est élevé, plus le talus est stable.',
    points: [
      'FoS > 1 : talus stable',
      'FoS ≈ 1 : état limite',
      'FoS < 1 : talus instable',
    ],
  },
];

export default function GuidePage() {
  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <section className="tool-panel">
        <div className="section-heading">
          <h2><span className="step-badge">?</span>Guide de présentation</h2>
          <span>FAQ projet</span>
        </div>
        <p className="max-w-4xl text-sm font-medium leading-7 text-slate-600">
          Cette page sert de support de présentation du projet de stabilité des talus développé
          avec la méthode de Spencer. Elle permet de résumer les objectifs du projet, le principe
          de calcul, les paramètres utilisés, l’interprétation des résultats ainsi que le
          fonctionnement général du programme développé.
        </p>
      </section>

      <div className="grid grid-cols-2 gap-4">
        {faqs.map((faq) => (
          <details key={faq.title} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" open={faq.tag === 'Vue globale'}>
            <summary className="cursor-pointer list-none">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-black uppercase tracking-wide text-slate-500">{faq.tag}</p>
                  <h3 className="mt-1 text-lg font-black text-slate-950">{faq.title}</h3>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-600">ouvrir</span>
              </div>
            </summary>
            <div className="mt-4 border-t border-slate-100 pt-4">
              <p className="text-sm font-medium leading-7 text-slate-600">{faq.body}</p>
              <ul className="mt-3 space-y-2">
                {faq.points.map((point) => (
                  <li key={point} className="rounded-md bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
