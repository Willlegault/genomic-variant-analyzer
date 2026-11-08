import pytest
import requests

import clinvar


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, headers: dict | None = None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self) -> dict:
        return self._payload


def _fake_ncbi(titles: dict[str, str]):
    """Stand-in for requests.get: esearch returns the ids in order, esummary their titles."""

    def get(url, params, timeout):
        if url.endswith("esearch.fcgi"):
            return _FakeResponse({"esearchresult": {"idlist": list(titles)}})
        result = {
            cid: {"title": title, "germline_classification": {"description": f"label-{cid}"}}
            for cid, title in titles.items()
        }
        return _FakeResponse({"result": result})

    return get


FOUNDER = {"17662": "NM_007294.4(BRCA1):c.68_69del (p.Glu23fs)"}


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    """Fresh cache and throttle per test; records sleeps instead of sleeping."""
    clinvar._cache.clear()
    monkeypatch.setattr(clinvar, "_last_request_at", 0.0)
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    recorded: list[float] = []
    monkeypatch.setattr(clinvar.time, "sleep", recorded.append)
    return recorded


def test_skips_fuzzy_hits_and_returns_exact_match(monkeypatch):
    monkeypatch.setattr(clinvar.requests, "get", _fake_ncbi({
        "55621": "NM_007294.4(BRCA1):c.5538G>A (p.Gln1846=)",
        "17662": "NM_007294.4(BRCA1):c.68_69del (p.Glu23fs)",
    }))
    result = clinvar.lookup("BRCA1", "c.68_69del")
    assert result["found"] is True
    assert result["clinvar_id"] == "17662"
    assert result["classification"] == "label-17662"


def test_no_exact_match_means_not_found(monkeypatch):
    monkeypatch.setattr(clinvar.requests, "get", _fake_ncbi({
        "3634711": "NM_007294.4(BRCA1):c.313T>G (p.Tyr105Asp)",
    }))
    result = clinvar.lookup("BRCA1", "c.181T>G", "p.Cys61Gly")
    assert result["found"] is False
    assert result["classification"] is None


def test_gene_must_match(monkeypatch):
    monkeypatch.setattr(clinvar.requests, "get", _fake_ncbi({
        "1": "NM_000059.4(BRCA2):c.68_69del (p.Glu23fs)",
    }))
    assert clinvar.lookup("BRCA1", "c.68_69del")["found"] is False


def test_rate_limited_request_is_retried(monkeypatch, sleeps):
    ok = _fake_ncbi(FOUNDER)
    calls = {"esearch": 0}

    def get(url, params, timeout):
        if url.endswith("esearch.fcgi"):
            calls["esearch"] += 1
            if calls["esearch"] == 1:
                return _FakeResponse({}, status_code=429, headers={"Retry-After": "2"})
        return ok(url, params, timeout)

    monkeypatch.setattr(clinvar.requests, "get", get)
    result = clinvar.lookup("BRCA1", "c.68_69del")
    assert result["found"] is True
    assert calls["esearch"] == 2
    assert 2.0 in sleeps  # honoured Retry-After


def test_long_retry_after_is_capped(monkeypatch, sleeps):
    ok = _fake_ncbi(FOUNDER)
    calls = {"esearch": 0}

    def get(url, params, timeout):
        if url.endswith("esearch.fcgi"):
            calls["esearch"] += 1
            if calls["esearch"] == 1:
                return _FakeResponse({}, status_code=429, headers={"Retry-After": "120"})
        return ok(url, params, timeout)

    monkeypatch.setattr(clinvar.requests, "get", get)
    assert clinvar.lookup("BRCA1", "c.68_69del")["found"] is True
    assert max(sleeps) == clinvar._MAX_RETRY_DELAY


def test_persistent_rate_limit_gives_up_with_error(monkeypatch):
    monkeypatch.setattr(
        clinvar.requests, "get", lambda url, params, timeout: _FakeResponse({}, status_code=429)
    )
    result = clinvar.lookup("BRCA1", "c.68_69del")
    assert result["found"] is False
    assert result["error"] == "ClinVar request failed: HTTPError"


def test_failed_lookup_is_not_cached(monkeypatch):
    monkeypatch.setattr(
        clinvar.requests, "get", lambda url, params, timeout: _FakeResponse({}, status_code=500)
    )
    assert clinvar.lookup("BRCA1", "c.68_69del")["error"] is not None

    # NCBI recovers: the next lookup must hit the network again, not the cache.
    monkeypatch.setattr(clinvar.requests, "get", _fake_ncbi(FOUNDER))
    result = clinvar.lookup("BRCA1", "c.68_69del")
    assert result["error"] is None
    assert result["found"] is True


def test_requests_are_spaced_to_ncbi_limit(monkeypatch, sleeps):
    monkeypatch.setattr(clinvar.requests, "get", _fake_ncbi(FOUNDER))
    clinvar.lookup("BRCA1", "c.68_69del")  # esearch + esummary back to back
    assert sleeps and max(sleeps) == pytest.approx(clinvar._MIN_INTERVAL, abs=0.05)


def test_api_key_is_sent_and_allows_faster_requests(monkeypatch, sleeps):
    monkeypatch.setenv("NCBI_API_KEY", "test-key")
    seen = []
    ok = _fake_ncbi(FOUNDER)

    def get(url, params, timeout):
        seen.append(params.get("api_key"))
        return ok(url, params, timeout)

    monkeypatch.setattr(clinvar.requests, "get", get)
    clinvar.lookup("BRCA1", "c.68_69del")
    assert seen == ["test-key", "test-key"]
    assert max(sleeps) <= clinvar._MIN_INTERVAL_WITH_KEY + 0.01


def test_conflicting_is_not_bucketed_as_pathogenic():
    assert clinvar.normalize_classification(
        "Conflicting classifications of pathogenicity"
    ) == "conflicting"
