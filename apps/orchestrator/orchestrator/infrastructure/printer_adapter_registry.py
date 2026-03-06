from orchestrator.application.ports import PrinterAdapterPort


class PrinterAdapterRegistry:
    def __init__(self, adapters: dict[str, PrinterAdapterPort] | None = None) -> None:
        self._adapters = {k.lower(): v for k, v in (adapters or {}).items()}

    def get(self, adapter_name: str | None) -> PrinterAdapterPort | None:
        if not adapter_name:
            return None
        return self._adapters.get(adapter_name.lower())
