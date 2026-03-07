from orchestrator.application.ports import (
    BackendGatewayPort,
)
from orchestrator.domain.models import PrinterRuntime
from orchestrator.domain.schemas import PrinterStateInput
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.infrastructure.state.live_machine_state import upsert_machine_state


class UpsertPrinterRuntimeUseCase:
    def __init__(
        self,
        backend_gateway: BackendGatewayPort,
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self.backend_gateway = backend_gateway
        self.domain_service = domain_service or OrchestratorDomainService()

    def execute(
        self,
        printer_id: str,
        data: PrinterStateInput,
        source_printer_ip: str | None = None,
        source_printer_mac: str | None = None,
        source_printer_serial: str | None = None,
    ) -> PrinterRuntime:
        row = self.domain_service.new_printer_runtime(printer_id)
        self.domain_service.apply_printer_state(
            row=row,
            data=data,
            source_printer_ip=source_printer_ip,
            source_printer_mac=source_printer_mac,
            source_printer_serial=source_printer_serial,
        )
        upsert_machine_state(
            printer_id,
            {
                "printer_id": printer_id,
                "status": row.status,
                "current_job_id": row.current_job_id,
                "progress_pct": row.progress_pct,
                "nozzle_temp_c": row.nozzle_temp_c,
                "bed_temp_c": row.bed_temp_c,
                "last_heartbeat_at": row.last_heartbeat_at.isoformat(),
            },
        )
        self.backend_gateway.post_printer_state(printer_id, self.domain_service.to_backend_payload(row))
        return row

