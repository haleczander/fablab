from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class PrinterBinding(SQLModel, table=True):
    __tablename__ = "printer_bindings"

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: str = Field(index=True, unique=True)
    printer_ip: str = Field(index=True, unique=True)
    printer_model: Optional[str] = None
    adapter_name: Optional[str] = None
