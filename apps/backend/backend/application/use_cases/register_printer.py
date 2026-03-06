from backend.application.app_services import PrinterAccessService
from backend.domain.models import BackendPrinter


class RegisterPrinterUseCase:
    def __init__(self, printer_access: PrinterAccessService) -> None:
        self.printer_access = printer_access

    def execute(self, printer_id: str) -> BackendPrinter:
        return self.printer_access.get_or_create(printer_id)

