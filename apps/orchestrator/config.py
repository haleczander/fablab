import os

ORCH_DATABASE_URL = os.getenv("ORCH_DATABASE_URL", "sqlite:////data/orchestrator.db")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "https://backend.example.com")
BACKEND_API_TOKEN = os.getenv("BACKEND_API_TOKEN", "")
BACKEND_TIMEOUT_S = float(os.getenv("BACKEND_TIMEOUT_S", "4"))
ORCH_HEARTBEAT_REFRESH_S = int(os.getenv("ORCH_HEARTBEAT_REFRESH_S", "60"))
ORCH_DISCOVERY_ENABLED = os.getenv("ORCH_DISCOVERY_ENABLED", "1").lower() in {"1", "true", "yes", "on"}
ORCH_DISCOVERY_CIDRS = os.getenv("ORCH_DISCOVERY_CIDRS", "172.25.0.0/24")
ORCH_DISCOVERY_INTERVAL_S = float(os.getenv("ORCH_DISCOVERY_INTERVAL_S", "30"))
ORCH_DISCOVERY_TIMEOUT_S = float(os.getenv("ORCH_DISCOVERY_TIMEOUT_S", "1.2"))
ORCH_DISCOVERY_MAX_HOSTS = int(os.getenv("ORCH_DISCOVERY_MAX_HOSTS", "256"))


