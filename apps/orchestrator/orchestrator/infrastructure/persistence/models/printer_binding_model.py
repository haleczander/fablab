from typing import Optional

from sqlmodel import Field, SQLModel

from orchestrator.domain.models import PrinterBinding


class SqlPrinterBinding(SQLModel, table=True):
    __tablename__ = "printer_bindings"

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: Optional[str] = Field(default=None, index=True, unique=True)
    printer_mac: str = Field(index=True, unique=True)
    printer_ip: Optional[str] = Field(default=None, index=True)
    printer_model: Optional[str] = Field(default=None)
    bound_at: Optional[str] = Field(default=None, index=True)
    is_ignored: bool = Field(default=False, index=True)

    def to_domain(self) -> PrinterBinding:
        return PrinterBinding(
            id=self.id,
            printer_id=self.printer_id,
            printer_mac=self.printer_mac,
            printer_ip=self.printer_ip,
            printer_model=self.printer_model,
            bound_at=self.bound_at,
            is_ignored=self.is_ignored,
        )

    @classmethod
    def from_domain(cls, binding: PrinterBinding) -> "SqlPrinterBinding":
        return cls(
            id=binding.id,
            printer_id=binding.printer_id,
            printer_mac=binding.printer_mac,
            printer_ip=binding.printer_ip,
            printer_model=binding.printer_model,
            bound_at=binding.bound_at,
            is_ignored=binding.is_ignored,
        )

    def update_from_domain(self, binding: PrinterBinding) -> None:
        self.printer_id = binding.printer_id
        self.printer_mac = binding.printer_mac
        self.printer_ip = binding.printer_ip
        self.printer_model = binding.printer_model
        self.bound_at = binding.bound_at
        self.is_ignored = binding.is_ignored
