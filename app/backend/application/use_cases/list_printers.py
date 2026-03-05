from app.backend.application.ports import PrinterRepositoryPort
from app.backend.domain.models import BackendPrinter


class ListPrintersUseCase:
    def __init__(self, printer_repo: PrinterRepositoryPort) -> None:
        self.printer_repo = printer_repo

    def execute(self) -> list[BackendPrinter]:
        return self.printer_repo.list_printers()
