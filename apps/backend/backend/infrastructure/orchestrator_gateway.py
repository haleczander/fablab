import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.application.exceptions import DispatchTargetNotFoundError, DispatchTemporaryError
from config import ORCHESTRATOR_INTERNAL_URL


class OrchestratorGateway:
    def enqueue_start_print(self, printer_id: str, job_id: str, est_duration_s: int) -> None:
        body = json.dumps({"job_id": job_id, "est_duration_s": est_duration_s}).encode("utf-8")
        url = f"{ORCHESTRATOR_INTERNAL_URL.rstrip('/')}/printers/{printer_id}/commands/start"
        request = Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        for i in range(2):
            try:
                with urlopen(request, timeout=4):
                    return
            except HTTPError as err:
                if err.code == 404:
                    raise DispatchTargetNotFoundError(f"printer_id inconnu dans orchestrateur: {printer_id}") from err
                if i == 0:
                    time.sleep(0.4)
                    continue
                raise DispatchTemporaryError(f"orchestrator HTTP error: {err.code}") from err
            except (URLError, TimeoutError) as err:
                if i == 0:
                    time.sleep(0.4)
                    continue
                raise DispatchTemporaryError("orchestrator unreachable") from err

