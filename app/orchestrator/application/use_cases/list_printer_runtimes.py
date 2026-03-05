from app.orchestrator.application.ports import PrinterRuntimeRepositoryPort
from app.orchestrator.domain.models import PrinterRuntime


class ListPrinterRuntimesUseCase:
    def __init__(self, printer_runtime_repo: PrinterRuntimeRepositoryPort) -> None:
        self.printer_runtime_repo = printer_runtime_repo

    def execute(self) -> list[PrinterRuntime]:
        return self.printer_runtime_repo.list_all()
