import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
)

from orchestrator.domain.schemas import PrinterStateInput


class PrusaLinkApiError(RuntimeError):
    pass


class PrusaLinkAdapter:
    def __init__(
        self,
        timeout_s: float = 4.0,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.timeout_s = timeout_s
        self.api_key = api_key.strip() if api_key else None

        opener = None
        if username and password:
            password_mgr = HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, uri="http://", user=username, passwd=password)
            auth_handler = HTTPDigestAuthHandler(password_mgr)
            opener = build_opener(auth_handler)
        self._opener = opener

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    def _request(self, printer_ip: str, path: str, method: str) -> tuple[int, str]:
        url = f"http://{printer_ip}{path}"
        request = Request(url=url, method=method, headers=self._headers())
        try:
            if self._opener is not None:
                with self._opener.open(request, timeout=self.timeout_s) as response:
                    return response.status, response.read().decode("utf-8", errors="ignore")
            from urllib.request import urlopen

            with urlopen(request, timeout=self.timeout_s) as response:
                return response.status, response.read().decode("utf-8", errors="ignore")
        except HTTPError as err:
            body = err.read().decode("utf-8", errors="ignore")
            return err.code, body
        except (URLError, TimeoutError) as err:
            raise PrusaLinkApiError(f"PrusaLink indisponible sur {printer_ip}: {err}") from err

    def _json_get(self, printer_ip: str, path: str) -> dict:
        status, body = self._request(printer_ip=printer_ip, path=path, method="GET")
        if status != 200:
            raise PrusaLinkApiError(f"PrusaLink GET {path} -> HTTP {status}")
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError as err:
            raise PrusaLinkApiError(f"Reponse JSON invalide sur {path}") from err

    def create_job(self, printer_ip: str, printer_file_path: str) -> str | None:
        normalized = printer_file_path.strip()
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        parts = normalized.split("/", 2)
        if len(parts) < 3 or not parts[1] or not parts[2]:
            raise ValueError("printer_file_path invalide, attendu: /<storage>/<fichier.gcode>")
        storage = quote(parts[1], safe="")
        rel_path = quote(parts[2], safe="/")
        endpoint = f"/api/v1/files/{storage}/{rel_path}"

        status, _ = self._request(printer_ip=printer_ip, path=endpoint, method="POST")
        if status not in {200, 201, 202, 204}:
            raise PrusaLinkApiError(f"PrusaLink start print refuse ({status}) sur {endpoint}")

        # PrusaLink ne renvoie pas forcement d'ID de job au start; on tente de le recuperer ensuite.
        job_status, body = self._request(printer_ip=printer_ip, path="/api/v1/job", method="GET")
        if job_status != 200 or not body:
            return None
        try:
            job = json.loads(body)
        except json.JSONDecodeError:
            return None
        job_id = job.get("id")
        return str(job_id) if job_id is not None else None

    def get_machine_info(self, printer_ip: str) -> dict:
        info = self._json_get(printer_ip=printer_ip, path="/api/v1/info")
        status = self._json_get(printer_ip=printer_ip, path="/api/v1/status")
        return {
            "adapter": "prusalink",
            "ip": printer_ip,
            "info": info,
            "status": status,
        }

    def get_machine_state(self, printer_ip: str) -> PrinterStateInput:
        payload = self._json_get(printer_ip=printer_ip, path="/api/v1/status")
        printer = payload.get("printer") or {}
        job = payload.get("job") or {}
        raw_state = str(printer.get("state", "IDLE")).upper()
        mapping = {
            "IDLE": "IDLE",
            "READY": "IDLE",
            "FINISHED": "IDLE",
            "STOPPED": "IDLE",
            "PRINTING": "PRINTING",
            "PAUSED": "IN_USE",
            "BUSY": "IN_USE",
            "ATTENTION": "ERROR",
            "ERROR": "ERROR",
        }
        status = mapping.get(raw_state, "ON")
        return PrinterStateInput(
            status=status,
            progress_pct=job.get("progress"),
            nozzle_temp_c=printer.get("temp_nozzle"),
            bed_temp_c=printer.get("temp_bed"),
            current_job_id=str(job.get("id")) if job.get("id") is not None else None,
        )
