from datetime import datetime

from pydantic import BaseModel, Field

PRINTER_ID_PATTERN = r"^PRN-[A-Za-z0-9_-]+$"


class RegisterPrinterInput(BaseModel):
    printer_id: str = Field(min_length=1, pattern=PRINTER_ID_PATTERN)


class PrinterStateReportInput(BaseModel):
    status: str
    last_heartbeat_at: datetime | None = None
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    current_job_id: str | None = None
