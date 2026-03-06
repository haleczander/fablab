from pydantic import BaseModel, Field, IPvAnyAddress, model_validator
from orchestrator.domain.mac import normalize_mac

PRINTER_ID_PATTERN = r"^PRN-[A-Za-z0-9_-]+$"


class BindPrinterInput(BaseModel):
    printer_id: str = Field(min_length=1, pattern=PRINTER_ID_PATTERN)
    printer_ip: IPvAnyAddress | None = None
    printer_mac: str | None = None
    printer_model: str | None = None

    @model_validator(mode="after")
    def validate_binding_target(self) -> "BindPrinterInput":
        if self.printer_mac and normalize_mac(self.printer_mac) is None:
            raise ValueError("printer_mac invalide")
        if self.printer_ip is None and not (self.printer_mac and self.printer_mac.strip()):
            raise ValueError("printer_ip ou printer_mac est requis")
        return self

