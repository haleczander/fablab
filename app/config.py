import os

ORCH_DATABASE_URL = os.getenv("ORCH_DATABASE_URL", "sqlite:////data/orchestrator.db")
BACKEND_DATABASE_URL = os.getenv("BACKEND_DATABASE_URL", "sqlite:////data/backend.db")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "https://backend.example.com")
BACKEND_API_TOKEN = os.getenv("BACKEND_API_TOKEN", "")
BACKEND_TIMEOUT_S = float(os.getenv("BACKEND_TIMEOUT_S", "4"))
ORCH_HEARTBEAT_REFRESH_S = int(os.getenv("ORCH_HEARTBEAT_REFRESH_S", "60"))
