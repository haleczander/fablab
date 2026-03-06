import json
import os
import socket
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrateur:8001").rstrip("/")
TICK_SECONDS = float(os.getenv("TICK_SECONDS", "15"))
PRINTER_MAC = os.getenv("PRINTER_MAC", "").strip()


def own_ip() -> str:
    return socket.gethostbyname(socket.gethostname())


def post_json(path: str, payload: dict) -> bool:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if PRINTER_MAC:
        headers["X-Printer-MAC"] = PRINTER_MAC
    request = Request(
        url=f"{ORCHESTRATOR_URL}{path}",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=4):
            return True
    except (URLError, TimeoutError):
        return False


def get_json(path: str) -> dict | None:
    headers = {}
    if PRINTER_MAC:
        headers["X-Printer-MAC"] = PRINTER_MAC
    request = Request(url=f"{ORCHESTRATOR_URL}{path}", headers=headers, method="GET")
    try:
        with urlopen(request, timeout=4) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None


def push_state(status: str, progress: float, job_id: str | None) -> bool:
    if status == "PRINTING":
        nozzle = 205.0
        bed = 60.0
    else:
        nozzle = 35.0
        bed = 30.0

    return post_json(
        "/devices/state-ingest",
        {
            "mac_address": PRINTER_MAC or None,
            "status": status,
            "progress_pct": progress,
            "nozzle_temp_c": nozzle,
            "bed_temp_c": bed,
            "current_job_id": job_id,
        },
    )


def poll_command() -> dict | None:
    return get_json("/devices/commands/next")


def main() -> None:
    ip_addr = own_ip()
    print(f"[SIM] start ip={ip_addr} mac={PRINTER_MAC or 'unknown'} orchestrator={ORCHESTRATOR_URL}", flush=True)

    status = "IDLE"
    progress = 0.0
    job_id = None
    started_at = 0.0
    est_duration_s = 900

    while True:
        if status == "IDLE":
            command = poll_command()
            if command and command.get("type") == "START_PRINT":
                status = "PRINTING"
                progress = 0.0
                job_id = str(command.get("job_id"))
                est_duration_s = int(command.get("est_duration_s", 900))
                started_at = time.time()
        else:
            elapsed = max(0.0, time.time() - started_at)
            progress = min(100.0, round((elapsed / est_duration_s) * 100.0, 2))
            if progress >= 100.0:
                status = "IDLE"
                job_id = None
                progress = 0.0

        ok = push_state(status, progress, job_id)
        if not ok:
            print("[SIM] state push failed", flush=True)
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main()
