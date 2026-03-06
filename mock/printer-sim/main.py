import json
import os
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

HOST = os.getenv("PRUSALINK_SIM_HOST", "0.0.0.0")
PORT = int(os.getenv("PRUSALINK_SIM_PORT", "80"))
PRINTER_NAME = os.getenv("PRINTER_NAME", "PrusaLink Sim")
PRINTER_SERIAL = os.getenv("PRINTER_SERIAL", "SIM-UNKNOWN-SN")
PRINTER_MODEL = os.getenv("PRINTER_MODEL", "MK4")
PRINT_DURATION_S = max(30, int(os.getenv("PRINT_DURATION_S", "900")))


class PrinterState:
    def __init__(self) -> None:
        self.current_job_id: int | None = None
        self.current_file_path: str | None = None
        self.started_at: float | None = None
        self.job_counter = 1000

    def _refresh(self) -> None:
        if self.current_job_id is None or self.started_at is None:
            return
        elapsed = max(0.0, time.time() - self.started_at)
        if elapsed >= PRINT_DURATION_S:
            self.current_job_id = None
            self.current_file_path = None
            self.started_at = None

    def start_print(self, file_path: str) -> int:
        self._refresh()
        self.job_counter += 1
        self.current_job_id = self.job_counter
        self.current_file_path = file_path
        self.started_at = time.time()
        return self.current_job_id

    def job_payload(self) -> dict | None:
        self._refresh()
        if self.current_job_id is None or self.started_at is None:
            return None
        elapsed = max(0, int(time.time() - self.started_at))
        progress = min(100.0, round((elapsed / PRINT_DURATION_S) * 100.0, 2))
        remaining = max(0, PRINT_DURATION_S - elapsed)
        return {
            "id": self.current_job_id,
            "state": "PRINTING",
            "progress": progress,
            "time_printing": elapsed,
            "time_remaining": remaining,
            "inaccurate_estimates": False,
            "file": {
                "name": (self.current_file_path or "").split("/")[-1] or "unknown.gcode",
                "display_name": (self.current_file_path or "").split("/")[-1] or "unknown.gcode",
                "path": "/".join((self.current_file_path or "/local").split("/")[:-1]) or "/local",
                "m_timestamp": int(time.time()),
            },
        }

    def status_payload(self) -> dict:
        job = self.job_payload()
        if job:
            return {
                "printer": {
                    "state": "PRINTING",
                    "temp_nozzle": 215.0,
                    "target_nozzle": 215.0,
                    "temp_bed": 60.0,
                    "target_bed": 60.0,
                },
                "job": {
                    "id": job["id"],
                    "progress": job["progress"],
                    "time_printing": job["time_printing"],
                    "time_remaining": job["time_remaining"],
                },
            }
        return {
            "printer": {
                "state": "IDLE",
                "temp_nozzle": 32.0,
                "target_nozzle": 0.0,
                "temp_bed": 29.0,
                "target_bed": 0.0,
            }
        }


STATE = PrinterState()


class Handler(BaseHTTPRequestHandler):
    server_version = "PrusaLinkSim/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, code: int, payload: dict | list) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, payload: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send_text(200, "PrusaLink simulator")
            return
        if path == "/api/version":
            self._send_json(200, {"api": "1.0.0", "server": "PrusaLink", "text": "PrusaLink simulator"})
            return
        if path == "/api/v1/info":
            hostname = socket.gethostname()
            self._send_json(
                200,
                {
                    "name": f"{PRINTER_NAME} {PRINTER_MODEL}",
                    "model": PRINTER_MODEL,
                    "serial": PRINTER_SERIAL,
                    "hostname": f"{hostname}.lan",
                    "mmu": False,
                    "farm_mode": False,
                    "nozzle_diameter": 0.4,
                    "min_extrusion_temp": 170,
                    "sd_ready": True,
                    "active_camera": False,
                    "location": "sim-net",
                },
            )
            return
        if path == "/api/v1/status":
            self._send_json(200, STATE.status_payload())
            return
        if path == "/api/v1/job":
            job = STATE.job_payload()
            if not job:
                self.send_response(204)
                self.end_headers()
                return
            self._send_json(200, job)
            return
        self._send_text(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/v1/files/"):
            # PrusaLink start print endpoint: /api/v1/files/{storage}/{path}
            rel = path[len("/api/v1/files/") :]
            rel = unquote(rel)
            if "/" not in rel:
                self._send_text(400, "invalid file path")
                return
            STATE.start_print("/" + rel.lstrip("/"))
            self.send_response(204)
            self.end_headers()
            return
        self._send_text(404, "Not found")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[PRUSALINK-SIM] listening on {HOST}:{PORT} serial={PRINTER_SERIAL} model={PRINTER_MODEL}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
