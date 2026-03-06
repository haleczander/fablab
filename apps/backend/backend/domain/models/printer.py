from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class BackendPrinter(SQLModel, table=True):
    __tablename__ = "backend_printers"

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: str = Field(index=True, unique=True)
    status: str = Field(default="OFF")
    last_heartbeat_at: Optional[datetime] = None
    current_job_id: Optional[str] = None
    progress_pct: Optional[float] = None
    nozzle_temp_c: Optional[float] = None
    bed_temp_c: Optional[float] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

