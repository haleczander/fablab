from sqlmodel import Session, select

from app.orchestrator.domain.models import DeviceRuntime


class SqlModelDeviceRuntimeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DeviceRuntime]:
        return list(self.session.exec(select(DeviceRuntime)).all())

    def get_by_ip(self, device_ip: str) -> DeviceRuntime | None:
        return self.session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == device_ip)).first()

    def save(self, row: DeviceRuntime) -> DeviceRuntime:
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row
