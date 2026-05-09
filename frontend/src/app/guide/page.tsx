const faqs = [
  {
    title: 'Résumé du projet',
    tag: 'Vue globale',
    body: 'Spencer est une application pédagogique de stabilité des talus. Elle permet de saisir une géométrie simple, des couches de sol, une nappe phréatique et des paramètres de calcul pour obtenir un facteur de sécurité et une surface de rupture critique.',
    points: ['Frontend Next.js pour la démonstration', 'Backend FastAPI pour les calculs', 'Méthode de Spencer appliquée aux surfaces circulaires', 'Lancement local simplifié par fichiers .bat'],
  },
  {
    title: 'Pourquoi la méthode de Spencer ?',
    tag: 'Méthode',
    body: 'La méthode de Spencer est une méthode d’équilibre limite qui vérifie la stabilité par tranches. Elle cherche un facteur de sécurité cohérent avec l’équilibre des moments et la fermeture des forces inter-tranches.',
    points: ['Découpage automatique du massif', 'Calcul des poids, pressions interstitielles et résistances', 'Recherche automatique de la surface critique', 'Interprétation directe du facteur FS'],
  },
  {
    title: 'Que représentent les couches de calcul ?',
    tag: 'Sol',
    body: 'Chaque couche représente un matériau géotechnique avec son poids volumique γ, sa cohésion effective c’ et son angle de frottement φ’. Ces paramètres influencent directement la résistance au cisaillement disponible.',
    points: ['γ contrôle le poids des tranches', 'c’ ajoute une résistance cohésive', 'φ’ contrôle la résistance par frottement', 'L’épaisseur organise la stratigraphie du talus'],
  },
  {
    title: 'Comment lire le facteur de sécurité ?',
    tag: 'Résultat',
    body: 'Le facteur FS compare les résistances disponibles aux efforts moteurs. Plus FS est élevé, plus le talus est stable dans le modèle étudié.',
    points: ['FS < 1.25 : instable ou critique', '1.25 ≤ FS < 1.5 : zone de vigilance', 'FS ≥ 1.5 : stabilité satisfaisante pour une lecture pédagogique', 'Toujours discuter les hypothèses de sol et de nappe'],
  },
  {
    title: 'Exemple réel à présenter',
    tag: 'Cas pratique',
    body: 'Exemple : talus routier de 10 m de hauteur et 15 m de projection, sol argileux c’=15 kPa, φ’=25°, γ=19 kN/m³. On compare le résultat sec avec le résultat en présence d’une nappe plus haute.',
    points: ['Cas sec : pression interstitielle faible', 'Cas humide : réduction de la contrainte effective', 'FS diminue généralement quand la nappe monte', 'Conclusion : drainage et maîtrise de l’eau sont des leviers majeurs'],
  },
  {
    title: 'Ce qu’il faut dire au professeur',
    tag: 'Soutenance',
    body: 'Le plus important est de montrer que l’application n’est pas seulement une interface : elle relie un modèle mécanique, des entrées géotechniques et une interprétation claire pour l’ingénieur.',
    points: ['Hypothèses affichées et contrôlables', 'Calcul reproductible localement', 'Visualisation directe du talus et du cercle critique', 'Architecture séparée : interface, API, cœur de calcul testé'],
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
          Cette page sert de support oral pour expliquer le projet à un professeur universitaire :
          objectif, méthode, paramètres, interprétation et exemples concrets.
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
