from app.backend.application.ports import JobRepositoryPort
from app.backend.domain.models import BackendJob


class ListJobsUseCase:
    def __init__(self, job_repo: JobRepositoryPort) -> None:
        self.job_repo = job_repo

    def execute(self) -> list[BackendJob]:
        return self.job_repo.list_jobs()
