from typing import Optional

from sqlmodel import Field, SQLModel


class PrinterBinding(SQLModel, table=True):
    __tablename__ = "printer_bindings"

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: Optional[str] = Field(default=None, index=True, unique=True)
    printer_mac: str = Field(index=True, unique=True)
    printer_ip: Optional[str] = Field(default=None, index=True)
    is_ignored: bool = Field(default=False, index=True)

