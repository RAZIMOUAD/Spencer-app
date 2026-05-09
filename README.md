# Spencer — Stabilité des Talus

Application d'analyse de stabilité des pentes par méthode de Spencer (EN 1997-1 / Eurocode 7).

---

## Pour l'utilisateur — Démarrage rapide (Windows)

### Prérequis à installer une seule fois

1. **Python 3.11 ou plus récent** : https://www.python.org/downloads/
   - Pendant l'installation, cochez **"Add Python to PATH"** ✅

2. **Node.js** (version LTS) : https://nodejs.org/
   - Choisissez la version marquée **"LTS"** (Long Term Support)
   - Utilisez Node 20 ou 22 ; évitez Node 23/24 pour ce projet

### Utilisation

| Fichier | Quand l'utiliser |
|---|---|
| `1_INSTALLER.bat` | **Une seule fois** après avoir reçu le projet |
| `2_LANCER.bat` | **A chaque fois** pour démarrer l'application |
| `3_ARRETER.bat` | Pour arrêter proprement l'application |

**Procédure normale :**
1. Double-cliquez sur `1_INSTALLER.bat` → attendez que ça finisse
2. Double-cliquez sur `2_LANCER.bat` → le navigateur s'ouvre automatiquement sur http://localhost:3000
3. Gardez la fenêtre `SPENCER - Demarrage et Arret` ouverte pendant la démo
4. Quand vous avez fini : revenez dans cette fenêtre et appuyez sur une touche → les serveurs s'arrêtent automatiquement

Si la fenêtre principale a été fermée par erreur, double-cliquez sur `3_ARRETER.bat` pour arrêter les serveurs restants.

---

## Architecture technique

```
spencer-app/
├── backend/          # API FastAPI + moteur de calcul Python
│   ├── app/          # Serveur HTTP, schémas, gestion d'erreurs
│   └── core/         # Logique métier pure (géométrie, Spencer, validation)
├── frontend/         # Interface Next.js + React + TypeScript + Tailwind
│   └── src/
│       ├── components/   # Composants UI par domaine
│       ├── store/        # État global (Zustand)
│       └── lib/          # Client API typé + types partagés
└── *.bat             # Scripts de lancement Windows
```

## Lancement développeur

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Tests backend
```bash
cd backend
.venv\Scripts\activate
pytest -v
```

## Modèles de données principaux

| Modèle | Description |
|---|---|
| `TerrainPoint` | Point (x, y) du profil du terrain |
| `SoilLayer` | Couche de sol : γ, c', φ', épaisseur |
| `WaterTable` | Nappe phréatique : élévation |
| `Circle` | Cercle de glissement : centre (cx, cy), rayon |
| `Slice` | Tranche : géométrie + forces |
| `SpencerSettings` | Paramètres du solveur : n_tranches, tolérance, max_iter |
| `AnalysisRequest` | Requête complète d'analyse |
| `AnalysisResult` | Résultat : FS, θ, convergence |

## API exposée

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/health` | Vérification de vie du serveur |
| POST | `/api/analysis/run` | Lance une analyse Spencer complète |
| POST | `/api/analysis/validate` | Valide la géométrie sans calculer |

## Statut

- ✅ Architecture complète (backend + frontend)
- ✅ Modèles de données typés (Pydantic v2 + TypeScript)
- ✅ Validation géométrique et mécanique
- ✅ 29 tests unitaires passent
- 🔲 Solveur Spencer (à implémenter)
- 🔲 Dessin canvas du profil (à connecter)
- 🔲 Recherche du cercle critique (à implémenter)
