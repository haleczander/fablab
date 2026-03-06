from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class DeviceRuntime(SQLModel, table=True):
    __tablename__ = "device_runtimes"

    id: Optional[int] = Field(default=None, primary_key=True)
    device_ip: str = Field(index=True, unique=True)
    device_mac: Optional[str] = Field(default=None, index=True, unique=True)
    device_serial: Optional[str] = Field(default=None, index=True, unique=True)
    is_bound: bool = Field(default=False)
    is_ignored: bool = Field(default=False, index=True)
    bound_printer_id: Optional[str] = Field(default=None, index=True)
    detected_model: Optional[str] = None
    detected_adapter: Optional[str] = None
    probe_reachable: bool = Field(default=False)
    status: str = Field(default="OFF")
    last_heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_job_id: Optional[str] = None
    progress_pct: Optional[float] = None
    nozzle_temp_c: Optional[float] = None
    bed_temp_c: Optional[float] = None
    last_printer_ip: Optional[str] = None
    last_printer_mac: Optional[str] = None
    last_printer_serial: Optional[str] = None

