from collections.abc import Callable

from orchestrator.application.use_cases.upsert_printer_runtime import UpsertPrinterRuntimeUseCase
from orchestrator.application.ports import PrinterAdapterResolverPort, PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterRuntime


class SyncPrinterStateUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        adapter_resolver: PrinterAdapterResolverPort,
        upsert_printer_runtime: UpsertPrinterRuntimeUseCase,
        discovery_snapshot_provider: Callable[[], list[dict[str, str | bool | int | float | None]]],
    ) -> None:
        self.binding_repo = binding_repo
        self.adapter_resolver = adapter_resolver
        self.upsert_printer_runtime = upsert_printer_runtime
        self.discovery_snapshot_provider = discovery_snapshot_provider

    def _resolve_snapshot(self, printer_mac: str) -> dict[str, str | bool | int | float | None] | None:
        for row in self.discovery_snapshot_provider():
            if str(row.get("device_mac") or "").strip() == printer_mac:
                return row
        return None

    def execute(self, printer_id: str) -> PrinterRuntime:
        binding = self.binding_repo.get_by_printer_id(printer_id)
        if not binding:
            raise LookupError(f"printer_id inconnu/non bind: {printer_id}")
        snapshot = self._resolve_snapshot(binding.printer_mac)
        printer_ip = (
            str(snapshot.get("device_ip") or "").strip()
            if snapshot and snapshot.get("device_ip") is not None
            else (binding.printer_ip or "")
        )
        if not printer_ip:
            raise ValueError(f"printer_ip manquant pour {printer_id}")

        adapter_name = str(snapshot.get("detected_adapter") or "").strip() if snapshot else ""
        adapter = self.adapter_resolver.get(adapter_name or None)
        if not adapter:
            raise ValueError(f"adapter non supporte pour {printer_id}: {adapter_name}")
        state = adapter.get_machine_state(printer_ip)
        return self.upsert_printer_runtime.execute(
            printer_id=printer_id,
            data=state,
            source_printer_ip=printer_ip,
            source_printer_mac=binding.printer_mac,
            source_printer_serial=str(snapshot.get("device_serial") or "") or None if snapshot else None,
        )
