"""ClinVar lookup via NCBI E-utilities.

Workflow:
    1. esearch?db=clinvar&term=<gene> <hgvs>  -> list of ClinVar IDs
    2. esummary?db=clinvar&id=<id1,id2,...>   -> per-record summaries
    3. keep the record whose title names exactly this variant

Step 3 matters: esearch is a fuzzy full-text search, and its first hit is often
a different variant in the same gene (for "c.181T>G" it ranks c.313T>G first).

The summary payload contains a `germline_classification.description` field that
holds the pathogenicity label ("Pathogenic", "Benign", "Uncertain significance",
etc.). Older API responses use `clinical_significance.description` — we read
both for forward compatibility.

Networked calls are wrapped in a TTL cache so a single analysis run that issues
N variant lookups doesn't hammer NCBI when the same variant appears repeatedly.
Only successful lookups are cached; a failed one is retried on the next request.

Rate limiting: E-utilities allows 3 requests/second per client, or 10 with an
API key (`NCBI_API_KEY`). Each lookup makes two requests, so an analysis with
several variants would exceed that and get HTTP 429. All requests go through
`_get`, which spaces them out and retries a 429 with backoff. The throttle is
per process, which matches the single-worker deployment.
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Any

import requests


_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_DEFAULT_TIMEOUT = 8  # seconds
_MAX_CANDIDATES = 20  # search hits checked for an exact match

# Seconds between requests: just over 1/3 s without a key, 1/10 s with one.
_MIN_INTERVAL = 0.34
_MIN_INTERVAL_WITH_KEY = 0.1
_MAX_RETRIES = 2  # extra attempts after a 429
_RETRY_BACKOFF = 1.0  # seconds, doubled on each retry unless Retry-After says otherwise

_throttle_lock = threading.Lock()
_last_request_at = 0.0

# "NM_007294.4(BRCA1):c.68_69del (p.Glu23fs)" -> ("BRCA1", "c.68_69del")
_TITLE_RE = re.compile(r"\(([^)]+)\):(c\.\S+)")
_CACHE_TTL = 60 * 60  # 1 hour
_CACHE_MAX = 1024

_cache: dict[str, tuple[float, dict]] = {}


def _cache_get(key: str) -> dict | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    return value


def _cache_put(key: str, value: dict) -> None:
    if len(_cache) >= _CACHE_MAX:
        # Drop the oldest 10% — cheap-and-cheerful eviction.
        oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[: _CACHE_MAX // 10]
        for k, _ in oldest:
            _cache.pop(k, None)
    _cache[key] = (time.time(), value)


def _email() -> str | None:
    return os.environ.get("NCBI_EMAIL") or None


def _api_key() -> str | None:
    return os.environ.get("NCBI_API_KEY") or None


def _common_params() -> dict[str, str]:
    params = {"retmode": "json", "tool": "genomic-variant-analyzer"}
    email = _email()
    if email:
        params["email"] = email
    api_key = _api_key()
    if api_key:
        params["api_key"] = api_key
    return params


def _wait_for_slot() -> None:
    """Block until enough time has passed since the previous NCBI request."""
    global _last_request_at
    interval = _MIN_INTERVAL_WITH_KEY if _api_key() else _MIN_INTERVAL
    with _throttle_lock:
        wait = _last_request_at + interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _retry_delay(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return float(retry_after)
    return _RETRY_BACKOFF * (2 ** attempt)


def _get(endpoint: str, params: dict[str, Any]) -> requests.Response:
    """GET an E-utilities endpoint, throttled, retrying when rate-limited."""
    for attempt in range(_MAX_RETRIES + 1):
        _wait_for_slot()
        response = requests.get(f"{_BASE}/{endpoint}", params=params, timeout=_DEFAULT_TIMEOUT)
        if response.status_code != 429 or attempt == _MAX_RETRIES:
            break
        time.sleep(_retry_delay(response, attempt))
    response.raise_for_status()
    return response


def _build_query(gene: str, hgvs_c: str, hgvs_p: str | None) -> str:
    # ClinVar's full-text search is forgiving — combining gene symbol with the
    # HGVS string usually surfaces the right record if one exists.
    parts = [f"{gene}[gene]", hgvs_c]
    if hgvs_p:
        parts.append(hgvs_p)
    return " ".join(parts)


def _classification_from_summary(summary: dict[str, Any]) -> str | None:
    """Extract a pathogenicity label, tolerating shape changes between API versions."""
    germline = summary.get("germline_classification")
    if isinstance(germline, dict):
        desc = germline.get("description")
        if isinstance(desc, str) and desc.strip():
            return desc.strip()

    legacy = summary.get("clinical_significance")
    if isinstance(legacy, dict):
        desc = legacy.get("description")
        if isinstance(desc, str) and desc.strip():
            return desc.strip()

    return None


def _title_matches(title: str | None, gene: str, hgvs_c: str) -> bool:
    match = _TITLE_RE.search(title or "")
    return bool(match) and match.group(1) == gene and match.group(2) == hgvs_c


def lookup(gene: str, hgvs_c: str, hgvs_p: str | None = None) -> dict:
    """Look up a single variant in ClinVar.

    Returns a dict shaped like:
        {
            "found": bool,
            "classification": str | None,    # e.g. "Pathogenic"
            "clinvar_id": str | None,
            "title": str | None,
            "query": str,
            "error": str | None,
        }
    Network/HTTP errors are caught and surfaced as `error` rather than raised,
    so a single flaky lookup never blows up an entire analysis response.
    """
    cache_key = f"{gene}|{hgvs_c}|{hgvs_p or ''}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    query = _build_query(gene, hgvs_c, hgvs_p)
    result: dict[str, Any] = {
        "found": False,
        "classification": None,
        "clinvar_id": None,
        "title": None,
        "query": query,
        "error": None,
    }

    try:
        search_params = {
            **_common_params(), "db": "clinvar", "term": query, "retmax": _MAX_CANDIDATES,
        }
        r = _get("esearch.fcgi", search_params)
        ids = r.json().get("esearchresult", {}).get("idlist", []) or []
        if not ids:
            _cache_put(cache_key, result)
            return result

        summary_params = {**_common_params(), "db": "clinvar", "id": ",".join(ids)}
        r2 = _get("esummary.fcgi", summary_params)
        summaries = r2.json().get("result", {}) or {}

        for clinvar_id in ids:
            summary = summaries.get(clinvar_id, {}) or {}
            if _title_matches(summary.get("title"), gene, hgvs_c):
                result.update({
                    "found": True,
                    "classification": _classification_from_summary(summary),
                    "clinvar_id": clinvar_id,
                    "title": summary.get("title"),
                })
                break
    except requests.RequestException as exc:
        result["error"] = f"ClinVar request failed: {exc.__class__.__name__}"
    except (ValueError, KeyError) as exc:
        result["error"] = f"ClinVar response parse error: {exc.__class__.__name__}"

    # A failure is usually transient (rate limit, timeout); caching it would
    # pin the error for the whole TTL.
    if result["error"] is None:
        _cache_put(cache_key, result)
    return result


def normalize_classification(label: str | None) -> str:
    """Bucket ClinVar's free-text labels into UI-friendly categories."""
    if not label:
        return "unknown"
    s = label.lower()
    # Order matters — "Conflicting classifications of pathogenicity" contains
    # "pathogenic" but isn't a pathogenic call, so check conflicting first.
    if "conflicting" in s:
        return "conflicting"
    if "uncertain" in s or "vus" in s:
        return "uncertain"
    if "likely pathogenic" in s:
        return "likely_pathogenic"
    if "likely benign" in s:
        return "likely_benign"
    if "pathogenic" in s:
        return "pathogenic"
    if "benign" in s:
        return "benign"
    return "other"
