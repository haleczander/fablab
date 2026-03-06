from backend.application.app_services import PrinterAccessService
from backend.application.exceptions import DispatchTemporaryError
from backend.application.ports import JobRepositoryPort, OrchestratorGatewayPort
from backend.domain.models import BackendJob
from backend.domain.schemas import CreateJobInput
from backend.domain.services import BackendDomainService
from urllib.parse import urlparse


class CreateJobUseCase:
    def __init__(
        self,
        job_repo: JobRepositoryPort,
        printer_access: PrinterAccessService,
        orchestrator_gateway: OrchestratorGatewayPort,
        domain_service: BackendDomainService | None = None,
    ) -> None:
        self.job_repo = job_repo
        self.printer_access = printer_access
        self.orchestrator_gateway = orchestrator_gateway
        self.domain_service = domain_service or BackendDomainService()

    def execute(self, data: CreateJobInput) -> BackendJob:
        self.printer_access.get_or_create(data.printer_id)
        job = self.domain_service.new_job(data)

        est_duration_s = _extract_est_duration_seconds(data.parameters)
        printer_file_path = _extract_printer_file_path(data.printer_file_path, data.parameters, data.gcode_url)
        try:
            self.orchestrator_gateway.enqueue_start_print(
                printer_id=job.printer_id,
                job_id=job.job_id,
                est_duration_s=est_duration_s,
                printer_file_path=printer_file_path,
            )
            self.domain_service.claim_next_job(job)
            job.message = "DISPATCHED_TO_ORCHESTRATOR"
            return self.job_repo.save(job)
        except DispatchTemporaryError:
            job.message = "ORCHESTRATOR_DISPATCH_FAILED"
            return self.job_repo.save(job)


def _extract_est_duration_seconds(parameters: dict[str, object]) -> int:
    for key in ("est_duration_s", "duration_s", "print_duration_s"):
        raw = parameters.get(key)
        if raw is None:
            continue
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        return max(30, min(86400, value))
    return 900


def _extract_printer_file_path(
    top_level_path: str | None,
    parameters: dict[str, object],
    gcode_url: str,
) -> str | None:
    if isinstance(top_level_path, str):
        value = top_level_path.strip()
        if value:
            return value

    for key in ("printer_file_path", "printerFilePath"):
        raw = parameters.get(key)
        if isinstance(raw, str):
            value = raw.strip()
            if value:
                return value

    # Backward-compatible fallback when front sends a direct path in gcode_url.
    value = gcode_url.strip()
    if value.startswith("/"):
        return value
    parsed = urlparse(value)
    path = (parsed.path or "").strip()
    if path and "/" in path:
        filename = path.rsplit("/", 1)[-1].strip()
        if filename:
            return f"/local/{filename}"
    return None

