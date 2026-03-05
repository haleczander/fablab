from app.orchestrator.application.ports import (
    BackendGatewayPort,
    PrinterRuntimeRepositoryPort,
)
from app.orchestrator.domain.models import PrinterRuntime
from app.orchestrator.domain.schemas import PrinterStateInput
from app.orchestrator.domain.services import OrchestratorDomainService


class UpsertPrinterRuntimeUseCase:
    def __init__(
        self,
        printer_runtime_repo: PrinterRuntimeRepositoryPort,
        backend_gateway: BackendGatewayPort,
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self.printer_runtime_repo = printer_runtime_repo
        self.backend_gateway = backend_gateway
        self.domain_service = domain_service or OrchestratorDomainService()

    def execute(self, printer_id: str, data: PrinterStateInput, source_printer_ip: str | None = None) -> PrinterRuntime:
        row = self.printer_runtime_repo.get_by_printer_id(printer_id)
        if not row:
            row = self.domain_service.new_printer_runtime(printer_id)

        self.domain_service.apply_printer_state(row=row, data=data, source_printer_ip=source_printer_ip)
        saved = self.printer_runtime_repo.save(row)
        self.backend_gateway.post_printer_state(printer_id, self.domain_service.to_backend_payload(saved))
        return saved
