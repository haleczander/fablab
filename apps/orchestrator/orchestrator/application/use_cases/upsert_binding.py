from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterBinding
from orchestrator.domain.services import OrchestratorDomainService


class UpsertBindingUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self.binding_repo = binding_repo
        self.domain_service = domain_service or OrchestratorDomainService()

    def execute(
        self,
        printer_id: str,
        printer_ip: str | None = None,
        printer_mac: str | None = None,
        printer_serial: str | None = None,
        printer_model: str | None = None,
        adapter_name: str | None = None,
    ) -> PrinterBinding:
        if not printer_mac:
            raise ValueError("printer_mac est requis")

        by_printer = self.binding_repo.get_by_printer_id(printer_id)
        by_mac = self.binding_repo.get_by_mac(printer_mac) if printer_mac else None
        target = by_printer or by_mac
        if target:
            if by_mac and by_mac.id != target.id:
                self.binding_repo.delete(by_mac)
            target.printer_id = printer_id
            target.printer_mac = printer_mac
            target.printer_ip = printer_ip or target.printer_ip
            target.is_ignored = False
            return self.binding_repo.save(target)

        created = self.domain_service.new_binding(
            printer_id=printer_id,
            printer_mac=printer_mac,
            printer_ip=printer_ip,
            is_ignored=False,
        )
        return self.binding_repo.save(created)

