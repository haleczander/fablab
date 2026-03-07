from orchestrator.application.ports import PrinterBindingRepositoryPort


class UnbindPrinterUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
    ) -> None:
        self._binding_repo = binding_repo

    def execute(self, printer_id: str) -> None:
        row = self._binding_repo.get_by_printer_id(printer_id)
        if not row:
            raise LookupError(f"binding introuvable pour {printer_id}")

        self._binding_repo.delete(row)
