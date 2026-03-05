from app.orchestrator.application.ports import DeviceRuntimeRepositoryPort, PrinterBindingRepositoryPort
from app.orchestrator.domain.models import PrinterBinding
from app.orchestrator.domain.services import OrchestratorDomainService


class UpsertBindingUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        device_runtime_repo: DeviceRuntimeRepositoryPort,
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self.binding_repo = binding_repo
        self.device_runtime_repo = device_runtime_repo
        self.domain_service = domain_service or OrchestratorDomainService()

    def execute(self, printer_id: str, printer_ip: str, printer_model: str | None = None) -> PrinterBinding:
        by_printer = self.binding_repo.get_by_printer_id(printer_id)
        by_ip = self.binding_repo.get_by_ip(printer_ip)

        device = self.device_runtime_repo.get_by_ip(printer_ip)
        detected_adapter = device.detected_adapter if device else None
        detected_model = device.detected_model if device else None
        effective_model = printer_model or detected_model

        if by_printer:
            old_ip = by_printer.printer_ip
            if by_ip and by_ip.id != by_printer.id:
                self.binding_repo.delete(by_ip)

            by_printer.printer_ip = printer_ip
            by_printer.adapter_name = detected_adapter
            by_printer.printer_model = effective_model
            saved = self.binding_repo.save(by_printer)
            if old_ip != printer_ip:
                old_device = self.device_runtime_repo.get_by_ip(old_ip)
                if old_device:
                    old_device.is_bound = False
                    old_device.bound_printer_id = None
                    self.device_runtime_repo.save(old_device)
            self._mark_device_binding(printer_ip, printer_id)
            return saved

        if by_ip:
            by_ip.printer_id = printer_id
            by_ip.adapter_name = detected_adapter
            by_ip.printer_model = effective_model
            saved = self.binding_repo.save(by_ip)
            self._mark_device_binding(printer_ip, printer_id)
            return saved

        created = self.domain_service.new_binding(
            printer_id=printer_id,
            printer_ip=printer_ip,
            printer_model=effective_model,
            adapter_name=detected_adapter,
        )
        saved = self.binding_repo.save(created)
        self._mark_device_binding(printer_ip, printer_id)
        return saved

    def _mark_device_binding(self, device_ip: str, printer_id: str) -> None:
        device = self.device_runtime_repo.get_by_ip(device_ip)
        if not device:
            return
        device.is_bound = True
        device.bound_printer_id = printer_id
        self.device_runtime_repo.save(device)
