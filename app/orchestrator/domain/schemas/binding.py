from pydantic import BaseModel, Field, IPvAnyAddress

PRINTER_ID_PATTERN = r"^PRN-[A-Za-z0-9_-]+$"


class BindPrinterInput(BaseModel):
    printer_id: str = Field(min_length=1, pattern=PRINTER_ID_PATTERN)
    printer_ip: IPvAnyAddress
    printer_model: str | None = None
