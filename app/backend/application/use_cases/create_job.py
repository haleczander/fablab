from app.backend.application.app_services import PrinterAccessService
from app.backend.application.ports import JobRepositoryPort
from app.backend.domain.models import BackendJob
from app.backend.domain.schemas import CreateJobInput
from app.backend.domain.services import BackendDomainService


class CreateJobUseCase:
    def __init__(
        self,
        job_repo: JobRepositoryPort,
        printer_access: PrinterAccessService,
        domain_service: BackendDomainService | None = None,
    ) -> None:
        self.job_repo = job_repo
        self.printer_access = printer_access
        self.domain_service = domain_service or BackendDomainService()

    def execute(self, data: CreateJobInput) -> BackendJob:
        self.printer_access.ensure_exists(data.printer_id)
        job = self.domain_service.new_job(data)
        return self.job_repo.save(job)
