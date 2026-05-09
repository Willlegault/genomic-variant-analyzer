"""Thin Supabase wrapper for analysis history persistence.

The app should remain usable without Supabase configured — if env vars are
missing we no-op all writes and return an empty list for reads, so local
development and CI runs don't require a Supabase project.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_TABLE = "analyses"
_client = None
_initialized = False


def _get_client():
    global _client, _initialized
    if _initialized:
        return _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not (url and key):
        logger.info("Supabase not configured (SUPABASE_URL/SUPABASE_KEY unset); history is disabled.")
        _initialized = True
        return None

    try:
        from supabase import create_client  # imported lazily so the dep is optional at runtime
        _client = create_client(url, key)
    except Exception as exc:  # noqa: BLE001 — surface ANY init failure as a soft-disable
        logger.warning("Supabase client init failed: %s — history will be disabled.", exc)
        _client = None

    _initialized = True
    return _client


def is_enabled() -> bool:
    return _get_client() is not None


def save_analysis(record: dict[str, Any]) -> dict | None:
    client = _get_client()
    if client is None:
        return None
    try:
        resp = client.table(_TABLE).insert(record).execute()
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase insert failed: %s", exc)
        return None


def list_analyses(limit: int = 25) -> list[dict]:
    client = _get_client()
    if client is None:
        return []
    try:
        resp = (
            client.table(_TABLE)
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return getattr(resp, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase select failed: %s", exc)
        return []
