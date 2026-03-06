from orchestrator.application.ports import DeviceRuntimeRepositoryPort, PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterBinding
from orchestrator.domain.services import OrchestratorDomainService


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

    def execute(
        self,
        printer_id: str,
        printer_ip: str | None = None,
        printer_mac: str | None = None,
        printer_model: str | None = None,
    ) -> PrinterBinding:
        if not printer_ip and not printer_mac:
            raise ValueError("printer_ip ou printer_mac est requis")

        by_printer = self.binding_repo.get_by_printer_id(printer_id)
        by_ip = self.binding_repo.get_by_ip(printer_ip) if printer_ip else None
        by_mac = self.binding_repo.get_by_mac(printer_mac) if printer_mac else None

        device = None
        if printer_mac:
            device = self.device_runtime_repo.get_by_mac(printer_mac)
        if not device and printer_ip:
            device = self.device_runtime_repo.get_by_ip(printer_ip)
        detected_adapter = device.detected_adapter if device else None
        detected_model = device.detected_model if device else None
        effective_model = printer_model or detected_model

        target = by_printer or by_mac or by_ip
        if target:
            old_ip = target.printer_ip
            old_mac = target.printer_mac
            if by_ip and by_ip.id != target.id:
                self.binding_repo.delete(by_ip)
            if by_mac and by_mac.id != target.id:
                self.binding_repo.delete(by_mac)

            target.printer_id = printer_id
            if printer_ip:
                target.printer_ip = printer_ip
            if printer_mac:
                target.printer_mac = printer_mac
            target.adapter_name = detected_adapter
            target.printer_model = effective_model
            saved = self.binding_repo.save(target)

            if old_ip and old_ip != saved.printer_ip:
                old_device = self.device_runtime_repo.get_by_ip(old_ip)
                if old_device:
                    old_device.is_bound = False
                    old_device.bound_printer_id = None
                    self.device_runtime_repo.save(old_device)
            if old_mac and old_mac != saved.printer_mac:
                old_device_by_mac = self.device_runtime_repo.get_by_mac(old_mac)
                if old_device_by_mac:
                    old_device_by_mac.is_bound = False
                    old_device_by_mac.bound_printer_id = None
                    self.device_runtime_repo.save(old_device_by_mac)

            self._mark_device_binding(device_ip=saved.printer_ip, device_mac=saved.printer_mac, printer_id=printer_id)
            return saved

        created = self.domain_service.new_binding(
            printer_id=printer_id,
            printer_ip=printer_ip,
            printer_mac=printer_mac,
            printer_model=effective_model,
            adapter_name=detected_adapter,
        )
        saved = self.binding_repo.save(created)
        self._mark_device_binding(device_ip=printer_ip, device_mac=printer_mac, printer_id=printer_id)
        return saved

    def _mark_device_binding(self, device_ip: str | None, device_mac: str | None, printer_id: str) -> None:
        device = None
        if device_mac:
            device = self.device_runtime_repo.get_by_mac(device_mac)
        if not device and device_ip:
            device = self.device_runtime_repo.get_by_ip(device_ip)
        if not device:
            return
        device.is_bound = True
        device.bound_printer_id = printer_id
        self.device_runtime_repo.save(device)

