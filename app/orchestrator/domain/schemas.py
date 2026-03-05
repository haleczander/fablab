from pydantic import BaseModel, Field, IPvAnyAddress

PRINTER_ID_PATTERN = r"^PRN-[A-Za-z0-9_-]+$"


class BindPrinterInput(BaseModel):
    printer_id: str = Field(min_length=1, pattern=PRINTER_ID_PATTERN)
    printer_ip: IPvAnyAddress


class PrinterStateInput(BaseModel):
    status: str
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    current_job_id: str | None = None


class PrinterIngestInput(BaseModel):
    printer_id: str = Field(min_length=1, pattern=PRINTER_ID_PATTERN)
    status: str
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    current_job_id: str | None = None
