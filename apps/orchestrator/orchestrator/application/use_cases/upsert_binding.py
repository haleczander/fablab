from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterBinding
from orchestrator.domain.services import OrchestratorDomainService


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
        printer_id: str,
        printer_ip: str | None = None,
        printer_mac: str | None = None,
        printer_serial: str | None = None,
        printer_model: str | None = None,
        adapter_name: str | None = None,
    ) -> PrinterBinding:
        _ = printer_serial, adapter_name
        if not printer_mac:
            raise ValueError("printer_mac est requis")

        by_printer = self._binding_repo.get_by_printer_id(printer_id)
        by_mac = self._binding_repo.get_by_mac(printer_mac)
        target = by_printer or by_mac
        if target:
            if by_mac and by_mac.id != target.id:
                self._binding_repo.delete(by_mac)
            target.printer_id = printer_id
            target.printer_mac = printer_mac
            target.printer_ip = printer_ip or target.printer_ip
            target.printer_model = printer_model or target.printer_model
            target.is_ignored = False
            return self._binding_repo.save(target)

        return self._binding_repo.save(
            self._domain_service.new_binding(
                printer_id=printer_id,
                printer_mac=printer_mac,
                printer_ip=printer_ip,
                printer_model=printer_model,
                is_ignored=False,
            )
        )

