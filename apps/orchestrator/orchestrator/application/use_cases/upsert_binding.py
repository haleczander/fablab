from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterBinding
from orchestrator.domain.services import OrchestratorDomainService, now_utc


class UpsertBindingUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self._binding_repo = binding_repo
        self._domain_service = domain_service or OrchestratorDomainService()

    def execute(
        self,
        printer_id: str | None = None,
        printer_ip: str | None = None,
        printer_mac: str | None = None,
        printer_model: str | None = None,
        adapter_name: str | None = None,
        is_ignored: bool = False,
    ) -> PrinterBinding:
        _ = adapter_name
        if not printer_mac:
            raise ValueError("printer_mac est requis")
        if not is_ignored and not printer_id:
            raise ValueError("printer_id est requis")

        by_printer = self._binding_repo.get_by_printer_id(printer_id) if printer_id else None
        by_mac = self._binding_repo.get_by_mac(printer_mac)
        target = by_printer or by_mac
        if target:
            if by_mac and by_mac.id != target.id:
                self._binding_repo.delete(by_mac)
            previous_printer_id = target.printer_id
            target.printer_id = printer_id
            target.printer_mac = printer_mac
            target.printer_ip = printer_ip or target.printer_ip
            target.printer_model = printer_model or target.printer_model
            target.is_ignored = is_ignored
            if printer_id and (target.bound_at is None or previous_printer_id != printer_id):
                target.bound_at = now_utc().isoformat()
            return self._binding_repo.save(target)

        return self._binding_repo.save(
            self._domain_service.new_binding(
                printer_id=printer_id,
                printer_mac=printer_mac,
                printer_ip=printer_ip,
                printer_model=printer_model,
                is_ignored=is_ignored,
            )
        )

