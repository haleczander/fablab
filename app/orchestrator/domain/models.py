from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class PrinterBinding(SQLModel, table=True):
    __tablename__ = "printer_bindings"

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: str = Field(index=True, unique=True)
    printer_ip: str = Field(index=True, unique=True)
    printer_model: Optional[str] = None
    adapter_name: Optional[str] = None


class PrinterRuntime(SQLModel, table=True):
    __tablename__ = "printer_runtimes"

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: str = Field(index=True, unique=True)
    status: str = Field(default="OFF")
    last_heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_job_id: Optional[str] = None
    progress_pct: Optional[float] = None
    nozzle_temp_c: Optional[float] = None
    bed_temp_c: Optional[float] = None
    last_printer_ip: Optional[str] = None


class DeviceRuntime(SQLModel, table=True):
    __tablename__ = "device_runtimes"

    id: Optional[int] = Field(default=None, primary_key=True)
    device_ip: str = Field(index=True, unique=True)
    is_bound: bool = Field(default=False)
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
