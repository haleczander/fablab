from orchestrator.application.ports import DeviceRuntimeRepositoryPort
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import DeviceRuntime


class SetDeviceIgnoredByMacUseCase:
    def __init__(self, device_runtime_repo: DeviceRuntimeRepositoryPort) -> None:
        self._device_runtime_repo = device_runtime_repo

    def execute(
        self,
        device_mac: str,
        device_ip: str,
        is_ignored: bool,
        device_serial: str | None = None,
        detected_adapter: str | None = None,
        detected_model: str | None = None,
    ) -> DeviceRuntime:
        mac = normalize_mac(device_mac)
        if not mac:
            raise ValueError("invalid device_mac")

        row = self._device_runtime_repo.get_by_mac(mac)
        if not row:
            if not is_ignored:
                raise LookupError("device not found")
            row = DeviceRuntime(
                device_ip=device_ip,
                device_mac=mac,
                device_serial=device_serial,
                detected_adapter=detected_adapter,
                detected_model=detected_model,
                probe_reachable=True,
            )

        row.is_ignored = is_ignored
        return self._device_runtime_repo.save(row)
