# Fablab Fleet Stack

Projet compose de 2 services applicatifs:
- `orchestrateur local` (edge, parle aux imprimantes)
- `backend + backoffice` (source de verite + UI operateur)

## Doctrine
- identifiant metier unique: `printer_id` (ex: `PRN-01`)
- IP imprimante uniquement pour mapping interne orchestrateur
- backend = source de verite (jobs, historique, registry)
- orchestrateur = agent d'execution tolerant aux coupures reseau

## Endpoints principaux
Orchestrateur (`app.main:app`):
- `GET /health`
- `GET /printers`
- `GET /printer-bindings`
- `POST /printer-bindings`
- `POST /printers/{printer_id}/state`
- `POST /printers/state-ingest`
- `POST /printers/{printer_id}/jobs/poll-once`

Backend (`app.backend_main:app`):
- `GET /health`
- `GET /printers`
- `POST /printers/register`
- `GET /printers/{printer_id}/next-job`
- `POST /printers/{printer_id}/state`
- `GET /jobs`
- `POST /jobs`
- `POST /jobs/{job_id}/progress`
- `GET /backoffice` (UI)

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

Backend + backoffice:
```bash
uvicorn app.backend_main:app --reload --port 8000
```

## Docker
Orchestrateur edge (proxy TLS + orchestrateur):
```bash
docker compose --env-file .env.orchestrateur -f compose.orchestrateur.yml up -d --build
```

Backend + backoffice:
```bash
docker compose --env-file .env.orchestrateur -f compose.backend.yml up -d --build
```

Cette stack lance:
- backend API: `http://localhost:8000` (ou `BACKEND_PORT`)
- backoffice: `http://localhost:8080` (ou `BACKOFFICE_PORT`) avec proxy API sur `/api/*`
- frontoffice placeholder: `http://localhost:8081` (ou `FRONTOFFICE_PORT`)
