from app.backend.application.app_services import PrinterAccessService
from app.backend.application.exceptions import DispatchTemporaryError
from app.backend.application.ports import JobRepositoryPort, OrchestratorGatewayPort
from app.backend.domain.models import BackendJob
from app.backend.domain.schemas import CreateJobInput
from app.backend.domain.services import BackendDomainService


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
        self.printer_access.ensure_exists(data.printer_id)
        job = self.domain_service.new_job(data)

        est_duration_s = _extract_est_duration_seconds(data.parameters)
        try:
            self.orchestrator_gateway.enqueue_start_print(
                printer_id=job.printer_id,
                job_id=job.job_id,
                est_duration_s=est_duration_s,
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
