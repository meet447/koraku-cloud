"""Build memory graph payloads for the Memory UI (Supermemory documents + fallbacks)."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from koraku.core.config import settings
from koraku.integrations.supermemory_client import _client, container_tag, supermemory_configured

log = logging.getLogger(__name__)

_SUPERMEMORY_DOCS_URL = "https://api.supermemory.ai/v3/documents/documents"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(value: Any) -> str:
    if value is None:
        return _now_iso()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _memory_lines_from_text(text: str | None) -> list[str]:
    lines: list[str] = []
    for raw in (text or "").splitlines():
        line = re.sub(r"^[-*]\s*", "", raw).strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _normalize_memory_entry(raw: dict[str, Any]) -> dict[str, Any]:
    mem_text = str(raw.get("memory") or raw.get("content") or "").strip()
    return {
        "id": str(raw.get("id") or uuid.uuid4()),
        "memory": mem_text,
        "content": raw.get("content"),
        "createdAt": _iso(raw.get("createdAt") or raw.get("created_at")),
        "updatedAt": _iso(raw.get("updatedAt") or raw.get("updated_at")),
        "spaceContainerTag": raw.get("spaceContainerTag") or raw.get("space_container_tag"),
        "isLatest": bool(raw.get("isLatest", raw.get("is_latest", True))),
        "relation": raw.get("relation"),
        "parentMemoryId": raw.get("parentMemoryId") or raw.get("parent_memory_id"),
        "rootMemoryId": raw.get("rootMemoryId") or raw.get("root_memory_id"),
        "memoryRelations": raw.get("memoryRelations") or raw.get("memory_relations"),
    }


def _normalize_document(raw: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(raw.get("id") or uuid.uuid4())
    mems_raw = raw.get("memories") or raw.get("memoryEntries") or raw.get("memory_entries") or []
    memories = [
        _normalize_memory_entry(m)
        for m in mems_raw
        if isinstance(m, dict) and str(m.get("memory") or m.get("content") or "").strip()
    ]
    return {
        "id": doc_id,
        "title": raw.get("title"),
        "url": raw.get("url"),
        "documentType": str(
            raw.get("documentType") or raw.get("document_type") or raw.get("type") or "text"
        ),
        "createdAt": _iso(raw.get("createdAt") or raw.get("created_at")),
        "updatedAt": _iso(raw.get("updatedAt") or raw.get("updated_at")),
        "summary": raw.get("summary") or raw.get("content"),
        "memories": memories,
    }


def _synthetic_document(
    doc_id: str,
    *,
    title: str,
    document_type: str,
    memory_lines: list[str],
    space_tag: str | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    memories: list[dict[str, Any]] = []
    for i, line in enumerate(memory_lines):
        text = line.strip()
        if not text:
            continue
        memories.append(
            {
                "id": f"{doc_id}-mem-{i}",
                "memory": text,
                "content": text,
                "createdAt": now,
                "updatedAt": now,
                "spaceContainerTag": space_tag,
                "isLatest": True,
                "isStatic": document_type == "profile-static",
            }
        )
    return {
        "id": doc_id,
        "title": title,
        "url": None,
        "documentType": document_type,
        "createdAt": now,
        "updatedAt": now,
        "summary": None,
        "memories": memories,
    }


def _profile_fallback_documents(
    profile: Any,
    *,
    space_tag: str,
    explicit_memory: str | None = None,
    explicit_soul: str | None = None,
) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    prof = getattr(profile, "profile", None)
    static: list[str] = []
    dynamic: list[str] = []
    if prof is not None:
        static = [str(x).strip() for x in (getattr(prof, "static", None) or []) if str(x).strip()]
        dynamic = [str(x).strip() for x in (getattr(prof, "dynamic", None) or []) if str(x).strip()]
    if static:
        docs.append(
            _synthetic_document(
                "koraku-profile-static",
                title="Learned — long-term",
                document_type="profile-static",
                memory_lines=static,
                space_tag=space_tag,
            )
        )
    if dynamic:
        docs.append(
            _synthetic_document(
                "koraku-profile-dynamic",
                title="Learned — recent",
                document_type="profile-dynamic",
                memory_lines=dynamic,
                space_tag=space_tag,
            )
        )
    explicit_lines = _memory_lines_from_text(explicit_memory)
    if explicit_lines:
        docs.append(
            _synthetic_document(
                "koraku-explicit-preferences",
                title="Explicit preferences",
                document_type="personalization",
                memory_lines=explicit_lines,
                space_tag=space_tag,
            )
        )
    soul_lines = _memory_lines_from_text(explicit_soul)
    if soul_lines:
        docs.append(
            _synthetic_document(
                "koraku-explicit-persona",
                title="Persona / soul",
                document_type="personalization-soul",
                memory_lines=soul_lines,
                space_tag=space_tag,
            )
        )
    return [d for d in docs if d.get("memories")]


def _fetch_supermemory_documents(
    tag: str,
    *,
    page: int,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    key = (settings.supermemory_api_key or "").strip()
    payload = {
        "page": max(1, int(page)),
        "limit": max(1, min(int(limit), 200)),
        "sort": "createdAt",
        "order": "desc",
        "containerTags": [tag],
    }
    with httpx.Client(timeout=45.0) as http:
        resp = http.post(
            _SUPERMEMORY_DOCS_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    docs_raw = data.get("documents") or []
    documents = [_normalize_document(d) for d in docs_raw if isinstance(d, dict)]
    documents = [d for d in documents if d.get("memories")]
    pagination = data.get("pagination") or {}
    normalized_pagination = {
        "currentPage": int(pagination.get("currentPage") or pagination.get("current_page") or page),
        "limit": int(pagination.get("limit") or limit),
        "totalItems": int(pagination.get("totalItems") or pagination.get("total_items") or len(documents)),
        "totalPages": int(pagination.get("totalPages") or pagination.get("total_pages") or 1),
    }
    return documents, normalized_pagination


def fetch_memory_graph_sync(
    user_id: str,
    *,
    org_id: str | None = None,
    page: int = 1,
    limit: int = 100,
    explicit_memory: str | None = None,
    explicit_soul: str | None = None,
) -> dict[str, Any]:
    """Documents + memories for @supermemory/memory-graph, scoped to this Koraku user."""
    uid = (user_id or "").strip()
    if not uid:
        return {
            "documents": [],
            "pagination": {"currentPage": 1, "limit": limit, "totalItems": 0, "totalPages": 0},
            "containerTag": "",
            "supermemoryConfigured": supermemory_configured(),
            "source": "empty",
        }
    tag = container_tag(uid, org_id)
    if not supermemory_configured():
        explicit_docs = _profile_fallback_documents(
            profile=None,
            space_tag=tag,
            explicit_memory=explicit_memory,
            explicit_soul=explicit_soul,
        )
        return {
            "documents": explicit_docs,
            "pagination": {
                "currentPage": 1,
                "limit": limit,
                "totalItems": len(explicit_docs),
                "totalPages": 1,
            },
            "containerTag": tag,
            "supermemoryConfigured": False,
            "source": "personalization_only",
        }

    documents: list[dict[str, Any]] = []
    pagination = {"currentPage": page, "limit": limit, "totalItems": 0, "totalPages": 0}
    source = "supermemory"
    try:
        documents, pagination = _fetch_supermemory_documents(tag, page=page, limit=limit)
    except Exception as e:
        log.warning("supermemory documents list failed: %s", e)
        source = "error"

    if not documents:
        try:
            profile = _client().profile(container_tag=tag)
            documents = _profile_fallback_documents(
                profile,
                space_tag=tag,
                explicit_memory=explicit_memory,
                explicit_soul=explicit_soul,
            )
            if documents:
                source = "profile_fallback"
                pagination = {
                    "currentPage": 1,
                    "limit": limit,
                    "totalItems": len(documents),
                    "totalPages": 1,
                }
        except Exception as e:
            log.warning("supermemory profile fallback failed: %s", e)
            documents = _profile_fallback_documents(
                profile=None,
                space_tag=tag,
                explicit_memory=explicit_memory,
                explicit_soul=explicit_soul,
            )
            if documents:
                source = "personalization_only"
    elif explicit_memory or explicit_soul:
        extra = _profile_fallback_documents(
            profile=None,
            space_tag=tag,
            explicit_memory=explicit_memory,
            explicit_soul=explicit_soul,
        )
        existing_ids = {d["id"] for d in documents}
        for doc in extra:
            if doc["id"] not in existing_ids:
                documents.append(doc)

    return {
        "documents": documents,
        "pagination": pagination,
        "containerTag": tag,
        "supermemoryConfigured": True,
        "source": source,
    }
