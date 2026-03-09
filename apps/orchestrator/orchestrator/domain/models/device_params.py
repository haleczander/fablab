from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeviceParams:
    status: str = "OFF"
    current_job_id: str | None = None
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    last_heartbeat_at: str | None = None
