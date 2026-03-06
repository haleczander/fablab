import os

BACKEND_DATABASE_URL = os.getenv("BACKEND_DATABASE_URL", "sqlite:////data/backend.db")
ORCHESTRATOR_INTERNAL_URL = os.getenv("ORCHESTRATOR_INTERNAL_URL", "http://orchestrateur:8001")
ORCHESTRATOR_WS_RETRY_S = float(os.getenv("ORCHESTRATOR_WS_RETRY_S", "2"))
BACKEND_QUEUE_RETRY_S = float(os.getenv("BACKEND_QUEUE_RETRY_S", "5"))

