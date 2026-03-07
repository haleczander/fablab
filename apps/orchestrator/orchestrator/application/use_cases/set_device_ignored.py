from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterBinding


class SetDeviceIgnoredUseCase:
    def __init__(self, binding_repo: PrinterBindingRepositoryPort) -> None:
        self._binding_repo = binding_repo

    def execute(self, device_id: int, is_ignored: bool) -> PrinterBinding:
        row = self._binding_repo.get_by_id(device_id)
        if not row:
            raise LookupError("device not found")
        row.is_ignored = is_ignored
        return self._binding_repo.save(row)
