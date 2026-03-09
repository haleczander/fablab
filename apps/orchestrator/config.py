import os


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


ORCH_DATABASE_URL = os.getenv("ORCH_DATABASE_URL", "sqlite:////data/orchestrator.db")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "https://backend.example.com")
BACKEND_API_TOKEN = os.getenv("BACKEND_API_TOKEN", "")
BACKEND_TIMEOUT_S = _env_float("BACKEND_TIMEOUT_S", 4.0)
ORCH_HEARTBEAT_REFRESH_S = _env_int("ORCH_HEARTBEAT_REFRESH_S", 60)
ORCH_DISCOVERY_ENABLED = os.getenv("ORCH_DISCOVERY_ENABLED", "1").lower() in {"1", "true", "yes", "on"}
ORCH_DISCOVERY_CIDRS = os.getenv("ORCH_DISCOVERY_CIDRS", "172.25.0.0/24")
ORCH_DISCOVERY_INTERVAL_S = _env_float("ORCH_DISCOVERY_INTERVAL_S", 300.0)
ORCH_BOUND_REFRESH_INTERVAL_S = _env_float("ORCH_BOUND_REFRESH_INTERVAL_S", 5.0)
ORCH_DISCOVERY_TIMEOUT_S = _env_float("ORCH_DISCOVERY_TIMEOUT_S", 1.2)
ORCH_PRUSALINK_TIMEOUT_S = _env_float("ORCH_PRUSALINK_TIMEOUT_S", 4.0)
ORCH_PRUSALINK_USERNAME = os.getenv("ORCH_PRUSALINK_USERNAME", "")
ORCH_PRUSALINK_PASSWORD = os.getenv("ORCH_PRUSALINK_PASSWORD", "")
ORCH_PRUSALINK_API_KEY = os.getenv("ORCH_PRUSALINK_API_KEY", "")


