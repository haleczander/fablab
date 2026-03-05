from pydantic import BaseModel, Field, IPvAnyAddress

PRINTER_ID_PATTERN = r"^PRN-[A-Za-z0-9_-]+$"


class BindPrinterInput(BaseModel):
    printer_id: str = Field(min_length=1, pattern=PRINTER_ID_PATTERN)
    printer_ip: IPvAnyAddress
    printer_model: str | None = None


class PrinterStateInput(BaseModel):
    status: str
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    current_job_id: str | None = None


class DeviceIngestInput(BaseModel):
    status: str
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    current_job_id: str | None = None


class FleetItem(BaseModel):
    printer_id: str
    printer_ip: str
    printer_model: str | None = None
    status: str | None = None
    last_heartbeat_at: str | None = None
    printer_ip: IPvAnyAddress | None = None


class StartPrintCommandInput(BaseModel):
    job_id: str | None = None
    est_duration_s: int = Field(default=900, ge=30, le=86400)
