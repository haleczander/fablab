from sqlmodel import Session, select

from orchestrator.domain.models import DeviceRuntime


class SqlModelDeviceRuntimeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DeviceRuntime]:
        return list(self.session.exec(select(DeviceRuntime)).all())

    def get_by_id(self, device_id: int) -> DeviceRuntime | None:
        return self.session.exec(select(DeviceRuntime).where(DeviceRuntime.id == device_id)).first()

    def get_by_ip(self, device_ip: str) -> DeviceRuntime | None:
        return self.session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == device_ip)).first()

    def get_by_mac(self, device_mac: str) -> DeviceRuntime | None:
        return self.session.exec(select(DeviceRuntime).where(DeviceRuntime.device_mac == device_mac)).first()

    def get_by_serial(self, device_serial: str) -> DeviceRuntime | None:
        return self.session.exec(select(DeviceRuntime).where(DeviceRuntime.device_serial == device_serial)).first()

    def save(self, row: DeviceRuntime) -> DeviceRuntime:
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

