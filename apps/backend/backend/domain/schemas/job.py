from typing import Any

from pydantic import AliasChoices, BaseModel, Field

from backend.domain.schemas.printer import PRINTER_ID_PATTERN


class CreateJobInput(BaseModel):
    printer_id: str = Field(
        min_length=1,
        pattern=PRINTER_ID_PATTERN,
        validation_alias=AliasChoices("printer_id", "printerId"),
    )
    gcode_url: str = Field(
        min_length=1,
        validation_alias=AliasChoices("gcode_url", "gcodeUrl"),
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("parameters", "params"),
    )
    printer_file_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices("printer_file_path", "printerFilePath"),
    )


class JobProgressInput(BaseModel):
    status: str
    progress_pct: float | None = None
    message: str | None = None

