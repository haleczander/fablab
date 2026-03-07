from collections.abc import Callable

from orchestrator.application.ports import PrinterAdapterResolverPort, PrinterBindingRepositoryPort


class CreatePrinterJobUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        adapter_resolver: PrinterAdapterResolverPort,
        discovery_snapshot_provider: Callable[[], list[dict[str, str | bool | int | float | None]]],
    ) -> None:
        self._binding_repo = binding_repo
        self._adapter_resolver = adapter_resolver
        self._discovery_snapshot_provider = discovery_snapshot_provider

    def _resolve_snapshot(self, printer_mac: str) -> dict[str, str | bool | int | float | None] | None:
        return next(
            (
                row
                for row in self._discovery_snapshot_provider()
                if str(row.get("device_mac") or "").strip() == printer_mac
            ),
            None,
        )

    def execute(self, printer_id: str, printer_file_path: str) -> dict[str, str | None]:
        binding = self._binding_repo.get_by_printer_id(printer_id)
        if not binding:
            raise LookupError(f"printer_id inconnu/non bind: {printer_id}")

        snapshot = self._resolve_snapshot(binding.printer_mac)
        printer_ip = str(snapshot.get("device_ip") or "").strip() if snapshot else (binding.printer_ip or "")
        if not printer_ip:
            raise ValueError(f"printer_ip manquant pour {printer_id}")

        adapter_name = str(snapshot.get("detected_adapter") or "").strip() if snapshot else ""
        adapter = self._adapter_resolver.get(adapter_name or None)
        if not adapter:
            raise ValueError(f"adapter non supporte pour {printer_id}: {adapter_name}")

        return {
            "adapter_name": adapter_name or None,
            "external_job_id": adapter.create_job(printer_ip, printer_file_path),
        }
