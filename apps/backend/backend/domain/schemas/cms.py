from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


LayoutMode = Literal["vertical", "horizontal", "grid"]
BlockKind = Literal["text", "links", "cta", "machines_feed", "image", "banner", "custom"]


class CmsBlock(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    body: str | None = Field(default=None, max_length=4000)
    image_url: str | None = Field(default=None, max_length=1000)
    kind: BlockKind = "custom"
    span_cols: int = Field(default=1, ge=1, le=6)
    span_rows: int = Field(default=1, ge=1, le=12)
    padding: int = Field(default=16, ge=0, le=120)
    margin_top: int = Field(default=0, ge=0, le=160)
    margin_bottom: int = Field(default=0, ge=0, le=160)
    font_size: int = Field(default=16, ge=10, le=64)
    font_family: str | None = Field(default=None, max_length=120)
    link_to_section_id: str | None = Field(default=None, max_length=80)


class CmsSection(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=140)
    slug: str = Field(min_length=1, max_length=120)
    show_in_nav: bool = True
    nav_label: str | None = Field(default=None, max_length=140)
    nav_group: str | None = Field(default=None, max_length=140)
    show_in_home: bool = True
    layout: LayoutMode = "vertical"
    columns: int = Field(default=1, ge=1, le=6)
    rows: int = Field(default=1, ge=1, le=12)
    gap: int = Field(default=16, ge=0, le=80)
    padding: int = Field(default=16, ge=0, le=120)
    margin_top: int = Field(default=0, ge=0, le=160)
    margin_bottom: int = Field(default=24, ge=0, le=160)
    blocks: list[CmsBlock] = Field(default_factory=list)


class CmsDraft(BaseModel):
    sections: list[CmsSection] = Field(default_factory=list)


class CmsSiteBundle(BaseModel):
    draft: CmsDraft
    published: CmsDraft
    published_version: int
    updated_at: datetime | None = None
    published_at: datetime | None = None


class CmsPublishedSite(BaseModel):
    published: CmsDraft
    published_version: int
    published_at: datetime | None = None
