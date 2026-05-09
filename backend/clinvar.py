"""ClinVar lookup via NCBI E-utilities.

Workflow:
    1. esearch?db=clinvar&term=<gene> <hgvs>  -> list of ClinVar IDs
    2. esummary?db=clinvar&id=<id1,id2,...>   -> per-record summaries

The summary payload contains a `germline_classification.description` field that
holds the pathogenicity label ("Pathogenic", "Benign", "Uncertain significance",
etc.). Older API responses use `clinical_significance.description` — we read
both for forward compatibility.

Networked calls are wrapped in a TTL cache so a single analysis run that issues
N variant lookups doesn't hammer NCBI when the same variant appears repeatedly.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests


_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_DEFAULT_TIMEOUT = 8  # seconds
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


def _common_params() -> dict[str, str]:
    params = {"retmode": "json", "tool": "genomic-variant-analyzer"}
    email = _email()
    if email:
        params["email"] = email
    return params


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
        search_params = {**_common_params(), "db": "clinvar", "term": query}
        r = requests.get(f"{_BASE}/esearch.fcgi", params=search_params, timeout=_DEFAULT_TIMEOUT)
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", []) or []
        if not ids:
            _cache_put(cache_key, result)
            return result

        clinvar_id = ids[0]
        summary_params = {**_common_params(), "db": "clinvar", "id": clinvar_id}
        r2 = requests.get(f"{_BASE}/esummary.fcgi", params=summary_params, timeout=_DEFAULT_TIMEOUT)
        r2.raise_for_status()
        summary = r2.json().get("result", {}).get(clinvar_id, {}) or {}

        result.update({
            "found": True,
            "classification": _classification_from_summary(summary),
            "clinvar_id": clinvar_id,
            "title": summary.get("title"),
        })
    except requests.RequestException as exc:
        result["error"] = f"ClinVar request failed: {exc.__class__.__name__}"
    except (ValueError, KeyError) as exc:
        result["error"] = f"ClinVar response parse error: {exc.__class__.__name__}"

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
