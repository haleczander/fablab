from orchestrator.application.ports import DeviceRuntimeRepositoryPort, PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterRuntime
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.application.use_cases.upsert_printer_runtime import UpsertPrinterRuntimeUseCase


class MarkJobSentUseCase:
    def __init__(
        self,
        upsert_printer_runtime: UpsertPrinterRuntimeUseCase,
        binding_repo: PrinterBindingRepositoryPort,
        device_runtime_repo: DeviceRuntimeRepositoryPort,
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self.upsert_printer_runtime = upsert_printer_runtime
        self.binding_repo = binding_repo
        self.device_runtime_repo = device_runtime_repo
        self.domain_service = domain_service or OrchestratorDomainService()

    def execute(self, printer_id: str, job_id: str) -> PrinterRuntime:
        runtime = self.upsert_printer_runtime.printer_runtime_repo.get_by_printer_id(printer_id)
        if not runtime:
            runtime = self.domain_service.new_printer_runtime(printer_id)

        self.domain_service.mark_job_sent(runtime, job_id)
        saved_runtime = self.upsert_printer_runtime.printer_runtime_repo.save(runtime)

        binding = self.binding_repo.get_by_printer_id(printer_id)
        if binding:
            device = None
            if binding.printer_mac:
                device = self.device_runtime_repo.get_by_mac(binding.printer_mac)
            if not device and binding.printer_ip:
                device = self.device_runtime_repo.get_by_ip(binding.printer_ip)
            if device:
                device.status = "IN_USE"
                device.current_job_id = job_id
                device.progress_pct = 0.0
                device.last_heartbeat_at = saved_runtime.last_heartbeat_at
                self.device_runtime_repo.save(device)

        self.upsert_printer_runtime.backend_gateway.post_printer_state(
            printer_id,
            self.domain_service.to_backend_payload(saved_runtime),
        )
        return saved_runtime

