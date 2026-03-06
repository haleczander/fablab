from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class BackendJob(SQLModel, table=True):
    __tablename__ = "backend_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(index=True, unique=True)
    printer_id: str = Field(index=True)
    gcode_url: str
    parameters_json: str = Field(default="{}")
    status: str = Field(default="QUEUED")
    progress_pct: Optional[float] = None
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    claimed_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

