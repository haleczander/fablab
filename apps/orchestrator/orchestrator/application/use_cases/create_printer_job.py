from orchestrator.application.ports import PrinterAdapterResolverPort, PrinterBindingRepositoryPort


class CreatePrinterJobUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        adapter_resolver: PrinterAdapterResolverPort,
    ) -> None:
        self.binding_repo = binding_repo
        self.adapter_resolver = adapter_resolver

    def execute(self, printer_id: str, printer_file_path: str) -> dict[str, str | None]:
        binding = self.binding_repo.get_by_printer_id(printer_id)
        if not binding:
            raise LookupError(f"printer_id inconnu/non bind: {printer_id}")
        if not binding.printer_ip:
            raise ValueError(f"printer_ip manquant pour {printer_id}")

        adapter = self.adapter_resolver.get(binding.adapter_name)
        if not adapter:
            raise ValueError(f"adapter non supporte pour {printer_id}: {binding.adapter_name}")

        job_id = adapter.create_job(binding.printer_ip, printer_file_path)
        return {
            "adapter_name": binding.adapter_name,
            "external_job_id": job_id,
        }
