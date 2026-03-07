from pydantic import BaseModel


class PrinterBinding(BaseModel):
    id: int | None = None
    printer_id: str | None = None
    printer_mac: str
    printer_ip: str | None = None
    printer_model: str | None = None
    is_ignored: bool = False

