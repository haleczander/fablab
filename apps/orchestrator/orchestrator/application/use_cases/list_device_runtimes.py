from orchestrator.application.ports import DeviceRuntimeRepositoryPort
from orchestrator.domain.models import DeviceRuntime


class ListDeviceRuntimesUseCase:
    def __init__(self, device_runtime_repo: DeviceRuntimeRepositoryPort) -> None:
        self.device_runtime_repo = device_runtime_repo

    def execute(self) -> list[DeviceRuntime]:
        return self.device_runtime_repo.list_all()

