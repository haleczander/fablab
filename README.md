# Fablab Fleet Stack

Projet compose de 3 services applicatifs:
- `orchestrateur local` (edge, parle aux imprimantes)
- `backend API` (source de verite metier)
- `backoffice/frontoffice` (apps Nuxt separees)

## Doctrine
- identifiant metier unique: `printer_id` (ex: `PRN-01`)
- IP imprimante uniquement pour mapping interne orchestrateur
- backend = source de verite (jobs, historique, registry)
- orchestrateur = agent d'execution tolerant aux coupures reseau
- fronts = clients web, sans logique metier backend

## Endpoints backend
Backend API (`app.backend_main:app`):
- `GET /health`
- `GET /printers`
- `POST /printers/register`
- `GET /printers/{printer_id}/next-job`
- `POST /printers/{printer_id}/state`
- `GET /jobs`
- `POST /jobs`
- `POST /jobs/{job_id}/progress`
- `GET /ws/printers` (WebSocket)

## Stack front (debutant)
- `Nuxt 3` choisi pour les 2 fronts (base Vue, prise en main simple).
- Backoffice: `web/backoffice`
- Frontoffice: `web/frontoffice`

## Lancer en local
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.orchestrateur.example .env.orchestrateur
```

Orchestrateur:
```bash
uvicorn app.main:app --reload --port 8001
```

Backend API:
```bash
uvicorn app.backend_main:app --reload --port 8000
```

Nuxt local (optionnel, hors Docker):
```bash
cd web/backoffice
npm install
npm run dev
```

```bash
cd web/frontoffice
npm install
npm run dev
```

## Docker
Orchestrateur edge (proxy TLS + orchestrateur):
```bash
docker compose --env-file .env.orchestrateur -f compose.orchestrateur.yml up -d --build
```
Dashboard orchestrateur via proxy: `https://localhost:8443/dashboard`

Backend API + backoffice + frontoffice:
```bash
docker compose --env-file .env.orchestrateur -f compose.backend.yml up -d --build
```

Cette stack lance:
- backend API: `http://localhost:8000` (ou `BACKEND_PORT`)
- backoffice Nuxt: `http://localhost:8080` (ou `BACKOFFICE_PORT`)
- frontoffice Nuxt: `http://localhost:8081` (ou `FRONTOFFICE_PORT`)

## Notes frontoffice
- Le frontoffice utilise surtout le flux `ws://<backend>/ws/printers` pour l'etat des machines.
- Fallback en polling `GET /printers` si le WebSocket n'est pas disponible.

Simulation imprimantes 3D (compose separe):
```bash
docker compose --env-file .env.orchestrateur -f compose.printers-sim.yml up -d --build
```
Pre-requis:
- l'orchestrateur doit deja tourner pour que le reseau `fablab_imp3d_net` existe
- les simus publient automatiquement leurs etats vers l'orchestrateur (`PRN-01..03`)
