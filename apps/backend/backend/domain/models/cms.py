from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class BackendCmsSite(SQLModel, table=True):
    __tablename__ = "backend_cms_sites"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_key: str = Field(index=True, unique=True)
    draft_json: str = Field(default="{}")
    published_json: str = Field(default="{}")
    published_version: int = Field(default=0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = None
