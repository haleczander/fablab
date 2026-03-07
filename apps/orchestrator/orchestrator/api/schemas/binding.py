from pydantic import BaseModel, Field, model_validator

from orchestrator.domain.models import MacAddress

PRINTER_ID_PATTERN = r"^PRN-[A-Za-z0-9_-]+$"


class BindingInput(BaseModel):
    printer_id: str | None = Field(default=None, min_length=1, pattern=PRINTER_ID_PATTERN)
    printer_mac: str
    printer_ip: str | None = None
    printer_model: str | None = None
    adapter_name: str | None = None
    is_ignored: bool = False

    @model_validator(mode="after")
    def validate_binding_target(self) -> "BindingInput":
        if MacAddress.parse(self.printer_mac) is None:
            raise ValueError("printer_mac invalide")
        if not self.is_ignored and not self.printer_id:
            raise ValueError("printer_id requis si le binding n'est pas ignore")
        return self
