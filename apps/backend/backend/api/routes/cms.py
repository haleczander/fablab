import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from backend.domain.models import BackendCmsSite
from backend.domain.schemas.cms import CmsDraft, CmsPublishedSite, CmsSection, CmsSiteBundle
from backend.infrastructure.db import get_session

router = APIRouter(tags=["backend-api"])
SITE_KEY = "frontoffice"
_published_cache: CmsPublishedSite | None = None


def _default_draft() -> CmsDraft:
    return CmsDraft(
        sections=[
            CmsSection(
                id="section-root",
                title=" ",
                slug="section-root",
                layout="vertical",
                columns=1,
                rows=1,
                show_in_nav=False,
                blocks=[],
            )
        ]
    )


def _safe_parse_draft(raw: str) -> CmsDraft:
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        payload = {}
    try:
        return CmsDraft.model_validate(payload)
    except Exception:
        return _default_draft()


def _ensure_site(session: Session) -> BackendCmsSite:
    row = session.exec(select(BackendCmsSite).where(BackendCmsSite.site_key == SITE_KEY)).first()
    if row:
        return row

    default_draft = _default_draft()
    draft_json = default_draft.model_dump_json()
    row = BackendCmsSite(
        site_key=SITE_KEY,
        draft_json=draft_json,
        published_json=draft_json,
        published_version=1,
        updated_at=datetime.now(timezone.utc),
        published_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _to_bundle(row: BackendCmsSite) -> CmsSiteBundle:
    draft = _safe_parse_draft(row.draft_json)
    published = _safe_parse_draft(row.published_json)
    return CmsSiteBundle(
        draft=draft,
        published=published,
        published_version=row.published_version,
        updated_at=row.updated_at,
        published_at=row.published_at,
    )


def _to_published(row: BackendCmsSite) -> CmsPublishedSite:
    return CmsPublishedSite(
        published=_safe_parse_draft(row.published_json),
        published_version=row.published_version,
        published_at=row.published_at,
    )


@router.get("/cms/frontoffice", response_model=CmsSiteBundle)
def get_frontoffice_bundle(session: Session = Depends(get_session)) -> CmsSiteBundle:
    row = _ensure_site(session)
    return _to_bundle(row)


@router.get("/cms/frontoffice/published", response_model=CmsPublishedSite)
def get_frontoffice_published(session: Session = Depends(get_session)) -> CmsPublishedSite:
    global _published_cache
    if _published_cache is not None:
        return _published_cache
    row = _ensure_site(session)
    _published_cache = _to_published(row)
    return _published_cache


@router.put("/cms/frontoffice/draft", response_model=CmsSiteBundle)
def save_frontoffice_draft(payload: CmsDraft, session: Session = Depends(get_session)) -> CmsSiteBundle:
    row = _ensure_site(session)
    row.draft_json = payload.model_dump_json()
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_bundle(row)


@router.post("/cms/frontoffice/publish", response_model=CmsSiteBundle)
def publish_frontoffice(session: Session = Depends(get_session)) -> CmsSiteBundle:
    global _published_cache
    row = _ensure_site(session)
    row.published_json = row.draft_json
    row.published_version += 1
    row.published_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    _published_cache = _to_published(row)
    return _to_bundle(row)
