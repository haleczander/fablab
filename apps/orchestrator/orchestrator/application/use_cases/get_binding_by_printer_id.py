from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterBinding


class GetBindingByPrinterIdUseCase:
    def __init__(self, binding_repo: PrinterBindingRepositoryPort) -> None:
        self.binding_repo = binding_repo

    def execute(self, printer_id: str) -> PrinterBinding | None:
        return self.binding_repo.get_by_printer_id(printer_id)

