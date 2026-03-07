from pydantic import BaseModel


class DeviceIgnoreInput(BaseModel):
    is_ignored: bool


class DeviceIgnoreByMacInput(BaseModel):
    device_mac: str
    device_ip: str
    is_ignored: bool
    device_serial: str | None = None
    detected_adapter: str | None = None
    detected_model: str | None = None
