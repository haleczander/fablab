from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import DeviceRuntime, PrinterRuntime
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.schemas import DeviceIngestInput, PrinterStateInput
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.application.use_cases.upsert_printer_runtime import UpsertPrinterRuntimeUseCase


class IngestDeviceStateUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        upsert_printer_runtime: UpsertPrinterRuntimeUseCase,
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self.binding_repo = binding_repo
        self.upsert_printer_runtime = upsert_printer_runtime
        self.domain_service = domain_service or OrchestratorDomainService()

    def execute(self, source_ip: str, data: DeviceIngestInput) -> tuple[DeviceRuntime, PrinterRuntime | None, bool]:
        source_mac = normalize_mac(data.mac_address)
        source_serial = data.serial_number.strip() if data.serial_number else None
        binding = self.binding_repo.get_by_mac(source_mac) if source_mac else None
        if not binding:
            binding = self.binding_repo.get_by_ip(source_ip)

        device = self.domain_service.new_device_runtime(source_ip, source_mac, source_serial)
        device.is_bound = binding is not None
        device.bound_printer_id = binding.printer_id if binding else None

        self.domain_service.apply_device_state(device, data, source_ip, source_mac, source_serial)

        if not binding:
            return device, None, False

        printer_state = PrinterStateInput(
            status=device.status,
            progress_pct=device.progress_pct,
            nozzle_temp_c=device.nozzle_temp_c,
            bed_temp_c=device.bed_temp_c,
            current_job_id=device.current_job_id,
        )
        runtime = self.upsert_printer_runtime.execute(
            printer_id=binding.printer_id,
            data=printer_state,
            source_printer_ip=source_ip,
            source_printer_mac=source_mac,
            source_printer_serial=source_serial,
        )
        if source_ip and binding.printer_ip != source_ip:
            binding.printer_ip = source_ip
            self.binding_repo.save(binding)
        return device, runtime, False

