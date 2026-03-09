from orchestrator.application.dependencies import autowired
from orchestrator.application.ports import PrinterBindingPersistencePort
from orchestrator.domain.models import PrinterBinding


class GetBindingByPrinterIdUseCase:
    binding_repo: PrinterBindingPersistencePort = autowired()

    def execute(self, printer_id: str) -> PrinterBinding | None:
        return self.binding_repo.get_by_printer_id(printer_id)

