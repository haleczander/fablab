import json
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.config import BACKEND_API_TOKEN, BACKEND_API_URL, BACKEND_TIMEOUT_S


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if BACKEND_API_TOKEN:
        headers["Authorization"] = f"Bearer {BACKEND_API_TOKEN}"
    return headers


def post_printer_state(printer_id: str, payload: dict) -> bool:
    url = f"{BACKEND_API_URL}/printers/{printer_id}/state"
    body = json.dumps(payload).encode("utf-8")
    request = Request(url=url, data=body, headers=_headers(), method="POST")
    for i in range(2):
        try:
            with urlopen(request, timeout=BACKEND_TIMEOUT_S):
                return True
        except (URLError, TimeoutError):
            if i == 0:
                time.sleep(0.4)
    return False


def get_next_job(printer_id: str) -> dict | None:
    url = f"{BACKEND_API_URL}/printers/{printer_id}/next-job"
    request = Request(url=url, headers=_headers(), method="GET")
    for i in range(2):
        try:
            with urlopen(request, timeout=BACKEND_TIMEOUT_S) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, json.JSONDecodeError):
            if i == 0:
                time.sleep(0.4)
    return None
