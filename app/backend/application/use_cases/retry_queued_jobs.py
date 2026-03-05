import json

from app.backend.application.exceptions import DispatchTargetNotFoundError, DispatchTemporaryError
from app.backend.application.ports import JobRepositoryPort, OrchestratorGatewayPort
from app.backend.domain.models import BackendJob
from app.backend.domain.services import BackendDomainService


class RetryQueuedJobsUseCase:
    def __init__(
        self,
        job_repo: JobRepositoryPort,
        orchestrator_gateway: OrchestratorGatewayPort,
        domain_service: BackendDomainService | None = None,
    ) -> None:
        self.job_repo = job_repo
        self.orchestrator_gateway = orchestrator_gateway
        self.domain_service = domain_service or BackendDomainService()

    def execute(self) -> list[BackendJob]:
        updated: list[BackendJob] = []
        for job in self.job_repo.list_queued_jobs():
            est_duration_s = _extract_est_duration_seconds(job.parameters_json)
            try:
                self.orchestrator_gateway.enqueue_start_print(
                    printer_id=job.printer_id,
                    job_id=job.job_id,
                    est_duration_s=est_duration_s,
                )
                self.domain_service.claim_next_job(job)
                job.message = "DISPATCHED_TO_ORCHESTRATOR"
            except DispatchTargetNotFoundError:
                job.message = "ORCHESTRATOR_TARGET_NOT_FOUND"
            except DispatchTemporaryError:
                job.message = "ORCHESTRATOR_DISPATCH_FAILED"
            updated.append(self.job_repo.save(job))
        return updated


def _extract_est_duration_seconds(parameters_json: str) -> int:
    try:
        parameters = json.loads(parameters_json) if parameters_json else {}
    except json.JSONDecodeError:
        parameters = {}
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
