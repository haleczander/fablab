from pydantic import BaseModel, Field, model_validator
from orchestrator.domain.mac import normalize_mac

PRINTER_ID_PATTERN = r"^PRN-[A-Za-z0-9_-]+$"


class BindPrinterInput(BaseModel):
    printer_id: str = Field(min_length=1, pattern=PRINTER_ID_PATTERN)
    printer_mac: str
    printer_ip: str | None = None
    printer_serial: str | None = None
    printer_model: str | None = None
    adapter_name: str | None = None

    @model_validator(mode="after")
    def validate_binding_target(self) -> "BindPrinterInput":
        if normalize_mac(self.printer_mac) is None:
            raise ValueError("printer_mac invalide")
        return self

