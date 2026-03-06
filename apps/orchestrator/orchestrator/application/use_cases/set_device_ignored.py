from orchestrator.application.ports import DeviceRuntimeRepositoryPort
from orchestrator.domain.models import DeviceRuntime


class SetDeviceIgnoredUseCase:
    def __init__(self, device_runtime_repo: DeviceRuntimeRepositoryPort) -> None:
        self._device_runtime_repo = device_runtime_repo

    def execute(self, device_id: int, is_ignored: bool) -> DeviceRuntime:
        row = self._device_runtime_repo.get_by_id(device_id)
        if not row:
            raise LookupError("device not found")
        row.is_ignored = is_ignored
        return self._device_runtime_repo.save(row)
