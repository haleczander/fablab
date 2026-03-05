from app.backend.application.ports import PrinterRepositoryPort
from app.backend.application.exceptions import PrinterNotRegisteredError
from app.backend.domain.models import BackendPrinter
from app.backend.domain.services import BackendDomainService


class PrinterAccessService:
    def __init__(
        self,
        printer_repo: PrinterRepositoryPort,
        domain_service: BackendDomainService | None = None,
    ) -> None:
        self.printer_repo = printer_repo
        self.domain_service = domain_service or BackendDomainService()

    def get_or_create(self, printer_id: str) -> BackendPrinter:
        printer = self.printer_repo.get_by_printer_id(printer_id)
        if printer:
            return printer
        return self.printer_repo.save(self.domain_service.new_printer(printer_id))

    def ensure_exists(self, printer_id: str) -> None:
        printer = self.printer_repo.get_by_printer_id(printer_id)
        if not printer:
            raise PrinterNotRegisteredError(f"printer_id inconnu: {printer_id}")
