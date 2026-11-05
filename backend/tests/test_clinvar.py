import pytest

import clinvar


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

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


@pytest.fixture(autouse=True)
def _empty_cache():
    clinvar._cache.clear()


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


def test_conflicting_is_not_bucketed_as_pathogenic():
    assert clinvar.normalize_classification(
        "Conflicting classifications of pathogenicity"
    ) == "conflicting"
