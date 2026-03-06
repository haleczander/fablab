from orchestrator.application.ports import PrinterAdapterResolverPort, PrinterBindingRepositoryPort


class GetPrinterMachineInfoUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        adapter_resolver: PrinterAdapterResolverPort,
    ) -> None:
        self.binding_repo = binding_repo
        self.adapter_resolver = adapter_resolver

    def execute(self, printer_id: str) -> dict:
        binding = self.binding_repo.get_by_printer_id(printer_id)
        if not binding:
            raise LookupError(f"printer_id inconnu/non bind: {printer_id}")
        if not binding.printer_ip:
            raise ValueError(f"printer_ip manquant pour {printer_id}")

        adapter = self.adapter_resolver.get(binding.adapter_name)
        if not adapter:
            raise ValueError(f"adapter non supporte pour {printer_id}: {binding.adapter_name}")
        payload = adapter.get_machine_info(binding.printer_ip)
        payload["printer_id"] = printer_id
        payload["binding"] = {
            "printer_ip": binding.printer_ip,
            "printer_mac": binding.printer_mac,
            "printer_serial": binding.printer_serial,
            "printer_model": binding.printer_model,
            "adapter_name": binding.adapter_name,
        }
        return payload
