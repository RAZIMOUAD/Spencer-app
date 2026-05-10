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
    points: ['FS < 1 : talus instable', 'FS = 1 : état limite d’équilibre', 'FS > 1 : talus stable dans le modèle étudié', 'Toujours discuter les hypothèses de sol et de nappe'],
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

const chapter4Slices = [
  ['1', '-8,08°', '2,109', '28,19', '-3,96'],
  ['2', '-6,14°', '2,100', '74,83', '-8,00'],
  ['3', '13,23°', '2,145', '100,76', '23,06'],
  ['4', '28,33°', '2,372', '101,14', '48,00'],
  ['5', '46,07°', '3,010', '46,98', '33,83'],
];

const chapter4Iterations = [
  ['0', 'Approximation initiale', 'N ≈ W cos α', '3,46', 'Valeur obtenue dans le cours.'],
  ['1', 'Raffinement des normales', 'N corrigé avec le FS précédent', '≈ 3,31', 'Les efforts normaux sont recalculés.'],
  ['2', 'Ajustement des forces inter-tranches', 'θ est ajusté pour fermer les forces', '≈ 3,26', 'L’équilibre horizontal est amélioré.'],
  ['3', 'Nouveau recalcul', 'Moments + forces vérifiés ensemble', '≈ 3,24', 'La variation de FS devient faible.'],
  ['4', 'Convergence pédagogique', '|FSᵢ - FSᵢ₋₁| faible', '≈ 3,2 à 3,3', 'Ordre de grandeur annoncé dans le cours.'],
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

      <section className="tool-panel">
        <div className="section-heading">
          <h2><span className="step-badge">4</span>Calcul Spencer - exemple du cours</h2>
          <span>Itérations</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">Données utilisées</p>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm font-semibold text-slate-700">
              <span>γ = 18 kN/m³</span>
              <span>c = 25 kPa</span>
              <span>φ = 5°</span>
              <span>R = 8,5 m</span>
              <span>w = 2,088 m</span>
              <span>5 tranches</span>
            </div>
            <p className="mt-3 text-xs font-medium leading-5 text-slate-500">
              La première ligne de calcul du professeur utilise une approximation simple :
              N ≈ W cos α. Les itérations suivantes raffinent ce résultat en recalculant
              les normales et l’inclinaison des forces inter-tranches.
            </p>
          </div>

          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs font-medium leading-5 text-amber-900">
            <p className="font-black uppercase tracking-wide">Note de cohérence</p>
            <p className="mt-2">
              Les longueurs Δl du tableau correspondent à Δl = w / cos α. C’est cette
              lecture qui permet de retrouver les valeurs 2,109 ; 2,100 ; 2,145 ; 2,372 ; 3,010.
            </p>
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                {['Tranche', 'α', 'Δl (m)', 'W (kN/m)', 'W sin α'].map((head) => (
                  <th key={head} className="px-3 py-2 font-black">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {chapter4Slices.map((row) => (
                <tr key={row[0]} className="font-semibold text-slate-700">
                  {row.map((cell) => <td key={cell} className="px-3 py-2">{cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">Effort moteur</p>
            <p className="mt-2 text-2xl font-black text-slate-950">Md ≈ 92,93</p>
            <p className="mt-1 text-xs font-medium text-slate-500">Σ W sin α en kN/m</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">Effort résistant</p>
            <p className="mt-2 text-2xl font-black text-slate-950">Mr ≈ 321,57</p>
            <p className="mt-1 text-xs font-medium text-slate-500">cohésion + frottement</p>
          </div>
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-xs font-black uppercase tracking-wide text-emerald-700">Première itération</p>
            <p className="mt-2 text-4xl font-black text-emerald-700">FS ≈ 3,46</p>
            <p className="mt-1 text-xs font-medium text-emerald-700">321,57 / 92,93</p>
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                {['Itération', 'Étape', 'Ce qui est raffiné', 'FS', 'Lecture'].map((head) => (
                  <th key={head} className="px-3 py-2 font-black">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {chapter4Iterations.map((row) => (
                <tr key={row[0]} className="font-semibold text-slate-700">
                  {row.map((cell) => <td key={cell} className="px-3 py-2">{cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 rounded-lg bg-slate-950 p-4 text-sm font-medium leading-6 text-white">
          Dans l’application, ce raffinement n’est pas demandé à l’utilisateur. Le backend
          recalcule automatiquement les tranches, les normales, les pressions interstitielles,
          les équilibres et les itérations jusqu’à convergence, puis affiche uniquement le
          facteur de sécurité final et le cercle critique.
        </div>
      </section>
    </div>
  );
}
