from app.backend.application.app_services import PrinterAccessService
from app.backend.application.ports import PrinterRepositoryPort
from app.backend.domain.models import BackendPrinter
from app.backend.domain.schemas import PrinterStateReportInput
from app.backend.domain.services import BackendDomainService


class ReportPrinterStateUseCase:
    def __init__(
        self,
        printer_repo: PrinterRepositoryPort,
        printer_access: PrinterAccessService,
        domain_service: BackendDomainService | None = None,
    ) -> None:
        self.printer_repo = printer_repo
        self.printer_access = printer_access
        self.domain_service = domain_service or BackendDomainService()

    def execute(self, printer_id: str, data: PrinterStateReportInput) -> BackendPrinter:
        printer = self.printer_access.get_or_create(printer_id)
        self.domain_service.apply_printer_state(printer, data)
        return self.printer_repo.save(printer)
