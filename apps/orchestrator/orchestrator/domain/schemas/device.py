from pydantic import BaseModel


class DeviceIngestInput(BaseModel):
    mac_address: str | None = None
    serial_number: str | None = None
    status: str
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    current_job_id: str | None = None


class DeviceIgnoreInput(BaseModel):
    is_ignored: bool


class DeviceIgnoreByMacInput(BaseModel):
    device_mac: str
    device_ip: str
    is_ignored: bool
    device_serial: str | None = None
    detected_adapter: str | None = None
    detected_model: str | None = None

