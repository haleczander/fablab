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

