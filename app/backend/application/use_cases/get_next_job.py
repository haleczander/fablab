from app.backend.application.ports import JobRepositoryPort
from app.backend.domain.services import BackendDomainService


class GetNextJobUseCase:
    def __init__(
        self,
        job_repo: JobRepositoryPort,
        domain_service: BackendDomainService | None = None,
    ) -> None:
        self.job_repo = job_repo
        self.domain_service = domain_service or BackendDomainService()

    def execute(self, printer_id: str) -> dict | None:
        job = self.job_repo.get_next_queued_for_printer(printer_id)
        if not job:
            return None
        payload = self.domain_service.claim_next_job(job)
        self.job_repo.save(job)
        return payload
