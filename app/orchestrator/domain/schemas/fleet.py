from pydantic import BaseModel


class FleetItem(BaseModel):
    printer_id: str
    printer_ip: str
    printer_model: str | None = None
    status: str | None = None
    last_heartbeat_at: str | None = None
