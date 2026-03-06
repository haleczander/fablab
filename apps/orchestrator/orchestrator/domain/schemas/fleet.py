from pydantic import BaseModel


class FleetItem(BaseModel):
    printer_id: str
    printer_ip: str | None = None
    printer_mac: str | None = None
    printer_serial: str | None = None
    printer_model: str | None = None
    adapter_name: str | None = None
    status: str | None = None
    last_heartbeat_at: str | None = None

