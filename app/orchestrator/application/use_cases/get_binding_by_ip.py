from app.orchestrator.application.ports import PrinterBindingRepositoryPort
from app.orchestrator.domain.models import PrinterBinding


class GetBindingByIpUseCase:
    def __init__(self, binding_repo: PrinterBindingRepositoryPort) -> None:
        self.binding_repo = binding_repo

    def execute(self, printer_ip: str) -> PrinterBinding | None:
        return self.binding_repo.get_by_ip(printer_ip)
