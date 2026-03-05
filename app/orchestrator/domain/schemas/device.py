from pydantic import BaseModel


class DeviceIngestInput(BaseModel):
    status: str
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    current_job_id: str | None = None
