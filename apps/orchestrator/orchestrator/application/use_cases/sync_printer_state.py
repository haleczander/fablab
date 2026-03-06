from orchestrator.application.use_cases.upsert_printer_runtime import UpsertPrinterRuntimeUseCase
from orchestrator.application.ports import PrinterAdapterResolverPort, PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterRuntime


class SyncPrinterStateUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        adapter_resolver: PrinterAdapterResolverPort,
        upsert_printer_runtime: UpsertPrinterRuntimeUseCase,
    ) -> None:
        self.binding_repo = binding_repo
        self.adapter_resolver = adapter_resolver
        self.upsert_printer_runtime = upsert_printer_runtime

    def execute(self, printer_id: str) -> PrinterRuntime:
        binding = self.binding_repo.get_by_printer_id(printer_id)
        if not binding:
            raise LookupError(f"printer_id inconnu/non bind: {printer_id}")
        if not binding.printer_ip:
            raise ValueError(f"printer_ip manquant pour {printer_id}")

        adapter = self.adapter_resolver.get(binding.adapter_name)
        if not adapter:
            raise ValueError(f"adapter non supporte pour {printer_id}: {binding.adapter_name}")
        state = adapter.get_machine_state(binding.printer_ip)
        return self.upsert_printer_runtime.execute(
            printer_id=printer_id,
            data=state,
            source_printer_ip=binding.printer_ip,
            source_printer_mac=binding.printer_mac,
            source_printer_serial=binding.printer_serial,
        )
