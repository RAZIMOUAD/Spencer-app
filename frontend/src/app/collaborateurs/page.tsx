type Member = {
  name: string;
  group: string;
};

const members: Member[] = [
  {
    name: 'OUHADDOU Jamal Eddine',
    group: 'EMSI Marrakech'
  },
  {
    name: 'ECHLIH Abdelmouhaimeine',
    group: 'EMSI Marrakech'
  },
  {
    name: 'SOUMIR Hatim',
    group: 'EMSI Marrakech'
  },
   {
    name: 'AIT BENMOUSSA Nissrine',
    group: 'EMSI Marrakech'
  },
];

export default function CollaborateursPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <section className="tool-panel">
        <div className="section-heading">
          <h2><span className="step-badge">1</span>Projet universitaire EMSI Marrakech</h2>
          <span>Équipe</span>
        </div>
        <div className="rounded-lg bg-slate-50 p-4 text-sm font-semibold leading-7 text-slate-600">
          Cette section présente les étudiants participant au projet Spencer dans un contexte universitaire
          à l'EMSI Marrakech. Les noms sont définis statiquement dans le code pour rester stables pendant la soutenance.
        </div>
        <div className="mt-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700">
          Professeur encadrant : <span className="text-slate-950">PR. CHERIF Seif Eddine</span>
        </div>
      </section>

      <section className="tool-panel">
        <div className="section-heading">
          <h2><span className="step-badge">2</span>Participants</h2>
          <span>{members.length} personne(s)</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {members.map((member) => (
            <article key={member.name} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-lg font-black text-slate-950">{member.name}</h3>
              <p className="mt-1 text-xs font-bold uppercase tracking-wide text-slate-500">{member.group}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
