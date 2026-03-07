from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class PrinterRuntime(SQLModel):
    id: Optional[int] = None
    printer_id: str
    status: str = "OFF"
    last_heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_job_id: Optional[str] = None
    progress_pct: Optional[float] = None
    nozzle_temp_c: Optional[float] = None
    bed_temp_c: Optional[float] = None
    last_printer_ip: Optional[str] = None
    last_printer_mac: Optional[str] = None
    last_printer_serial: Optional[str] = None

