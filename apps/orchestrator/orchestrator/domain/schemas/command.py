from pydantic import BaseModel, Field


class StartPrintCommandInput(BaseModel):
    job_id: str | None = None
    est_duration_s: int = Field(default=900, ge=30, le=86400)
    printer_file_path: str | None = None

