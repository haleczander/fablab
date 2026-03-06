# Fablab Fleet Stack

Projet compose de 4 applications:
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
Backend API (`apps/backend/main.py`):
- `GET /health`
- `GET /printers`
- `POST /printers/register`
- `GET /printers/{printer_id}/next-job`
- `POST /printers/{printer_id}/state`
- `GET /jobs`
- `POST /jobs`
- `POST /jobs/{job_id}/progress`
- `GET /cms/frontoffice`
- `PUT /cms/frontoffice/draft`
- `POST /cms/frontoffice/publish`
- `GET /cms/frontoffice/published`
- `GET /ws/machines` (WebSocket)

## Stack front (debutant)
- `Nuxt 3` choisi pour les 2 fronts (base Vue, prise en main simple).
- Backoffice: `apps/back-office`
- Frontoffice: `apps/front-office`

## Lancer en local
```bash
python -m venv .venv
.venv\Scripts\activate
copy .env.orchestrateur.example .env.orchestrateur
```

Orchestrateur:
```bash
cd apps/orchestrator
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Backend API:
```bash
cd apps/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Nuxt local (optionnel, hors Docker):
```bash
cd apps/back-office
npm install
npm run dev
```

```bash
cd apps/front-office
npm install
npm run dev
```

## Docker
Orchestrateur edge (proxy TLS + orchestrateur):
```bash
docker compose --env-file .env.orchestrateur -f compose.orchestrateur.yml up -d --build
```
Dashboard orchestrateur via proxy: `https://localhost:8443/dashboard`
Si `deploy/certs/fullchain.pem` et `deploy/certs/privkey.pem` sont absents, le reverse proxy genere un certificat auto-signe au demarrage.

Backend API + backoffice + frontoffice:
```bash
docker compose --env-file .env.orchestrateur -f compose.backend.yml up -d --build
```

Cette stack lance:
- backend API: `http://localhost:8000` (ou `BACKEND_PORT`)
- backoffice Nuxt: `http://localhost:8080` (ou `BACKOFFICE_PORT`)
- frontoffice Nuxt: `http://localhost:8081` (ou `FRONTOFFICE_PORT`)
- en Docker, Nuxt utilise `http://backend:8000` en interne pour le SSR et `BACKEND_PUBLIC_URL` pour le navigateur

## Notes frontoffice
- Le frontoffice charge le snapshot publie via `GET /cms/frontoffice/published`.
- Le bloc `machines_feed` ouvre ensuite `ws://<backend>/ws/machines` pour l'etat des machines.

## Notes backend
- Le backend applique ses migrations au demarrage via la table `schema_migrations`.

Simulation imprimantes 3D (compose separe):
```bash
docker compose --env-file .env.orchestrateur -f compose.printers-sim.yml up -d --build
```
Pre-requis:
- l'orchestrateur doit deja tourner pour que le reseau `fablab_imp3d_net` existe
- les simus publient automatiquement leurs etats vers l'orchestrateur (`PRN-01..03`)
