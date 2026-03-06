from backend.application.ports import JobRepositoryPort
from backend.domain.models import BackendJob
from backend.domain.schemas import JobProgressInput
from backend.domain.services import BackendDomainService


class UpdateJobProgressUseCase:
    def __init__(
        self,
        job_repo: JobRepositoryPort,
        domain_service: BackendDomainService | None = None,
    ) -> None:
        self.job_repo = job_repo
        self.domain_service = domain_service or BackendDomainService()

    def execute(self, job_id: str, data: JobProgressInput) -> BackendJob | None:
        job = self.job_repo.get_by_job_id(job_id)
        if not job:
            return None
        self.domain_service.apply_job_progress(job, data)
        return self.job_repo.save(job)

