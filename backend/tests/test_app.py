import pytest

import app as app_module
import clinvar
from references import BRCA1_CDS_HEAD as REF


@pytest.fixture
def client(monkeypatch):
    calls: list[str] = []

    def fake_lookup(gene, hgvs_c, hgvs_p=None):
        calls.append(hgvs_c)
        return {"found": True, "classification": "Pathogenic", "clinvar_id": "1",
                "title": None, "query": hgvs_c, "error": None}

    monkeypatch.setattr(clinvar, "lookup", fake_lookup)
    monkeypatch.setattr(app_module.supabase_client, "save_analysis", lambda record: None)
    test_client = app_module.app.test_client()
    test_client.lookups = calls
    return test_client


def _with_snps(count: int) -> str:
    """Reference with `count` substitutions, one every 9 bases (far enough apart to align cleanly)."""
    seq = list(REF)
    for i in range(count):
        pos = 3 + i * 9
        seq[pos] = "A" if seq[pos] != "A" else "C"
    return "".join(seq)


def test_clinvar_lookups_are_capped_per_analysis(client):
    resp = client.post("/api/analyze", json={"sequence": _with_snps(15)})
    assert resp.status_code == 200
    variants = resp.get_json()["variants"]
    assert len(variants) == 15

    assert len(client.lookups) == app_module.MAX_CLINVAR_LOOKUPS
    checked = variants[: app_module.MAX_CLINVAR_LOOKUPS]
    unchecked = variants[app_module.MAX_CLINVAR_LOOKUPS:]
    assert all(v["pathogenicity"] == "pathogenic" for v in checked)
    assert all(v["pathogenicity"] == "not_checked" for v in unchecked)
    assert all("first 12" in v["clinvar"]["reason"] for v in unchecked)


def test_lookups_stop_when_time_budget_is_spent(client, monkeypatch):
    clock = iter(range(0, 1000, 15))  # each monotonic() call advances 15 s
    monkeypatch.setattr(app_module.time, "monotonic", lambda: next(clock))
    variants = client.post("/api/analyze", json={"sequence": _with_snps(4)}).get_json()["variants"]
    assert [v["pathogenicity"] for v in variants].count("not_checked") >= 1
    assert "slow" in variants[-1]["clinvar"]["reason"]


def test_skip_clinvar_marks_variants_not_checked(client):
    resp = client.post("/api/analyze", json={"sequence": _with_snps(2), "skip_clinvar": True})
    variants = resp.get_json()["variants"]
    assert client.lookups == []
    assert {v["pathogenicity"] for v in variants} == {"not_checked"}


def test_invalid_sequence_is_rejected(client):
    resp = client.post("/api/analyze", json={"sequence": "ATGX"})
    assert resp.status_code == 400
    assert "Invalid bases" in resp.get_json()["error"]
