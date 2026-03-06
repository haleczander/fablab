from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterBinding


class GetBindingBySerialUseCase:
    def __init__(self, repo: PrinterBindingRepositoryPort) -> None:
        self.repo = repo

    def execute(self, printer_serial: str) -> PrinterBinding | None:
        return self.repo.get_by_serial(printer_serial)
