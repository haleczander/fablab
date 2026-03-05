from typing import Any

from pydantic import BaseModel, Field

from app.backend.domain.schemas.printer import PRINTER_ID_PATTERN


class CreateJobInput(BaseModel):
    printer_id: str = Field(min_length=1, pattern=PRINTER_ID_PATTERN)
    gcode_url: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class JobProgressInput(BaseModel):
    status: str
    progress_pct: float | None = None
    message: str | None = None
