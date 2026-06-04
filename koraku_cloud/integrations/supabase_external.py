"""Phone linking and iMessage thread persistence (Supabase service role)."""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from koraku_cloud.integrations.supabase_chat_history import supabase_chat_history_configured
from koraku_cloud.integrations.supabase_rest import get_http_client, headers as rest_headers, rest_url
from koraku.integrations.sendblue_client import normalize_e164
from koraku_cloud.integrations.supabase_tenant import ensure_personal_org_sync

log = logging.getLogger(__name__)

IMESSAGE_THREAD_TITLE = "iMessage"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def lookup_user_by_phone_sync(phone_e164: str) -> dict[str, Any] | None:
    if not supabase_chat_history_configured():
        return None
    phone = normalize_e164(phone_e164)
    if not phone:
        return None
    url = rest_url("/koraku_phone_link")
    params = {"phone_e164": f"eq.{phone}", "select": "user_id,org_id,imessage_thread_id,phone_e164"}
    r = get_http_client().get(url, headers=rest_headers(), params=params)
    if r.status_code != 200:
        return None
    rows = r.json()
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    return row if isinstance(row, dict) else None


def get_phone_link_for_user_sync(user_id: str) -> dict[str, Any] | None:
    if not supabase_chat_history_configured():
        return None
    url = rest_url("/koraku_phone_link")
    params = {"user_id": f"eq.{user_id}", "select": "phone_e164,imessage_thread_id,verified_at"}
    r = get_http_client().get(url, headers=rest_headers(), params=params)
    if r.status_code != 200:
        return None
    rows = r.json()
    if not rows:
        return None
    return rows[0] if isinstance(rows[0], dict) else None


def resolve_thread_channel_sync(thread_id: str, user_id: str) -> str:
    """Return ``web`` or ``imessage`` for workspace routing (defaults to ``web``).

    ``user_id`` must be the Supabase auth sub (not ``org_id/user_id`` storage scope).
    """
    from koraku.integrations.cloud_user import auth_user_id_from_storage_scope

    tid = (thread_id or "").strip()
    uid = auth_user_id_from_storage_scope((user_id or "").strip())
    if not tid or not uid:
        return "web"
    if not supabase_chat_history_configured():
        return "web"

    link = get_phone_link_for_user_sync(uid)
    if link and str(link.get("imessage_thread_id") or "").strip() == tid:
        return "imessage"

    try:
        url = rest_url("/chat_thread")
        params = {
            "id": f"eq.{tid}",
            "user_id": f"eq.{uid}",
            "select": "channel",
            "limit": "1",
        }
        r = get_http_client().get(url, headers=rest_headers(), params=params)
        if r.status_code == 200:
            rows = r.json()
            if isinstance(rows, list) and rows:
                ch = str((rows[0] or {}).get("channel") or "").strip().lower()
                if ch == "imessage":
                    return "imessage"
    except Exception as e:
        log.debug("resolve_thread_channel_sync failed thread=%s: %s", tid[:12], e)

    return "web"


def _upsert_thread_sync(*, thread_id: str, user_id: str, org_id: str) -> None:
    url = rest_url("/chat_thread")
    payload = {
        "id": thread_id,
        "user_id": user_id,
        "org_id": org_id,
        "title": IMESSAGE_THREAD_TITLE,
        "channel": "imessage",
        "pinned": True,
        "updated_at": _now_iso(),
    }
    get_http_client().post(
        url,
        headers={**rest_headers(), "Prefer": "resolution=merge-duplicates"},
        params={"on_conflict": "id"},
        json=payload,
    )


def ensure_imessage_thread_sync(user_id: str, org_id: str) -> str:
    existing = get_phone_link_for_user_sync(user_id)
    if existing and existing.get("imessage_thread_id"):
        return str(existing["imessage_thread_id"])
    thread_id = str(uuid.uuid4())
    _upsert_thread_sync(thread_id=thread_id, user_id=user_id, org_id=org_id)
    return thread_id


def link_phone_sync(*, user_id: str, org_id: str, phone_e164: str, thread_id: str) -> None:
    phone = normalize_e164(phone_e164)
    if not phone:
        raise ValueError("invalid phone")
    url = rest_url("/koraku_phone_link")
    payload = {
        "user_id": user_id,
        "org_id": org_id,
        "phone_e164": phone,
        "imessage_thread_id": thread_id,
        "verified_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    get_http_client().post(
        url,
        headers={**rest_headers(), "Prefer": "resolution=merge-duplicates"},
        params={"on_conflict": "user_id"},
        json=payload,
    )
    _upsert_thread_sync(thread_id=thread_id, user_id=user_id, org_id=org_id)


def append_thread_message_sync(*, thread_id: str, role: str, text: str) -> None:
    if not text.strip():
        return
    msg_id = str(uuid.uuid4())
    url = rest_url("/chat_message")
    content = {"text": text.strip()}
    if role == "assistant":
        content["run"] = {
            "assistantMarkdown": text.strip(),
            "streamStatus": "completed",
            "assistantBubbleMode": "final",
        }
    payload = {
        "id": msg_id,
        "thread_id": thread_id,
        "role": role,
        "content_json": content,
        "created_at": _now_iso(),
    }
    client = get_http_client()
    client.post(url, headers=rest_headers(), json=payload)
    client.patch(
        rest_url("/chat_thread"),
        headers=rest_headers(),
        params={"id": f"eq.{thread_id}"},
        json={"updated_at": _now_iso()},
    )


def start_verification_sync(*, user_id: str, phone_e164: str) -> str:
    """Create a 6-digit code; returns plaintext code for outbound SMS."""
    phone = normalize_e164(phone_e164)
    if not phone:
        raise ValueError("invalid phone")
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    url = rest_url("/koraku_phone_verification")
    payload = {
        "user_id": user_id,
        "phone_e164": phone,
        "code_hash": _hash_code(code),
        "expires_at": expires.isoformat(),
    }
    get_http_client().post(url, headers=rest_headers(), json=payload)
    return code


def confirm_verification_sync(*, user_id: str, phone_e164: str, code: str) -> str:
    """Verify code, link phone, return imessage thread id."""
    phone = normalize_e164(phone_e164)
    if not phone:
        raise ValueError("invalid phone")
    org_id = ensure_personal_org_sync(user_id)
    if not org_id:
        raise ValueError("organization unavailable")
    url = rest_url("/koraku_phone_verification")
    params = {
        "user_id": f"eq.{user_id}",
        "phone_e164": f"eq.{phone}",
        "order": "created_at.desc",
        "limit": "1",
    }
    r = get_http_client().get(url, headers=rest_headers(), params=params)
    if r.status_code != 200:
        raise ValueError("verification lookup failed")
    rows = r.json()
    if not rows:
        raise ValueError("no pending verification")
    row = rows[0]
    exp = row.get("expires_at") or ""
    if exp:
        try:
            exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            if exp_dt < datetime.now(timezone.utc):
                raise ValueError("code expired")
        except ValueError:
            raise
    if row.get("code_hash") != _hash_code(code.strip()):
        raise ValueError("invalid code")
    thread_id = ensure_imessage_thread_sync(user_id, org_id)
    link_phone_sync(user_id=user_id, org_id=org_id, phone_e164=phone, thread_id=thread_id)
    return thread_id


def try_confirm_from_inbound_message_sync(*, phone_e164: str, body: str) -> dict[str, Any] | None:
    """If body is a verification code, link phone to pending user and return link row."""
    phone = normalize_e164(phone_e164)
    text = (body or "").strip()
    if not phone or not re_match_code(text):
        return None
    code = text.replace("KORAKU-", "").replace("koraku-", "").strip()
    if len(code) != 6 or not code.isdigit():
        return None
    url = rest_url("/koraku_phone_verification")
    params = {
        "phone_e164": f"eq.{phone}",
        "order": "created_at.desc",
        "limit": "1",
    }
    r = get_http_client().get(url, headers=rest_headers(), params=params)
    if r.status_code != 200:
        return None
    rows = r.json()
    if not rows:
        return None
    row = rows[0]
    user_id = str(row.get("user_id") or "")
    if not user_id:
        return None
    if row.get("code_hash") != _hash_code(code):
        return None
    org_id = ensure_personal_org_sync(user_id)
    if not org_id:
        return None
    thread_id = ensure_imessage_thread_sync(user_id, org_id)
    link_phone_sync(user_id=user_id, org_id=org_id, phone_e164=phone, thread_id=thread_id)
    return lookup_user_by_phone_sync(phone)


def re_match_code(text: str) -> bool:
    import re

    t = text.strip()
    if re.fullmatch(r"\d{6}", t):
        return True
    if re.fullmatch(r"(?i)koraku-\d{6}", t):
        return True
    return False
