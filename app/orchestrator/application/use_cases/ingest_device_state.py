from app.orchestrator.application.ports import (
    DeviceRuntimeRepositoryPort,
    PrinterBindingRepositoryPort,
)
from app.orchestrator.domain.models import DeviceRuntime, PrinterRuntime
from app.orchestrator.domain.schemas import DeviceIngestInput, PrinterStateInput
from app.orchestrator.domain.services import OrchestratorDomainService
from app.orchestrator.application.use_cases.upsert_printer_runtime import UpsertPrinterRuntimeUseCase


class IngestDeviceStateUseCase:
    def __init__(
        self,
        device_runtime_repo: DeviceRuntimeRepositoryPort,
        binding_repo: PrinterBindingRepositoryPort,
        upsert_printer_runtime: UpsertPrinterRuntimeUseCase,
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self.device_runtime_repo = device_runtime_repo
        self.binding_repo = binding_repo
        self.upsert_printer_runtime = upsert_printer_runtime
        self.domain_service = domain_service or OrchestratorDomainService()

    def execute(self, source_ip: str, data: DeviceIngestInput) -> tuple[DeviceRuntime, PrinterRuntime | None]:
        device = self.device_runtime_repo.get_by_ip(source_ip)
        if not device:
            device = self.domain_service.new_device_runtime(source_ip)

        binding = self.binding_repo.get_by_ip(source_ip)
        device.is_bound = binding is not None
        device.bound_printer_id = binding.printer_id if binding else None

        self.domain_service.apply_device_state(device, data, source_ip)
        saved_device = self.device_runtime_repo.save(device)

        if not binding:
            return saved_device, None

        printer_state = PrinterStateInput(
            status=saved_device.status,
            progress_pct=saved_device.progress_pct,
            nozzle_temp_c=saved_device.nozzle_temp_c,
            bed_temp_c=saved_device.bed_temp_c,
            current_job_id=saved_device.current_job_id,
        )
        runtime = self.upsert_printer_runtime.execute(
            printer_id=binding.printer_id,
            data=printer_state,
            source_printer_ip=source_ip,
        )
        return saved_device, runtime
