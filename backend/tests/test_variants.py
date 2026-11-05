from references import BRCA1_CDS_HEAD as REF
from variants import detect_variants


def _single(query: str):
    variants = detect_variants(REF, query)
    assert len(variants) == 1, variants
    return variants[0]


def test_identical_sequence_has_no_variants():
    assert detect_variants(REF, REF) == []


def test_missense_brca1_c61g():
    v = _single(REF[:180] + "G" + REF[181:])
    assert v.hgvs_c == "c.181T>G"
    assert v.hgvs_p == "p.Cys61Gly"
    assert v.effect == "missense"


def test_founder_deletion_is_named_at_3prime_position():
    # Deleting either AG of the AGAG repeat at 66-69 gives the same sequence;
    # HGVS and ClinVar call it c.68_69del.
    for start in (65, 67):
        v = _single(REF[:start] + REF[start + 2:])
        assert v.hgvs_c == "c.68_69del"
        assert v.effect == "frameshift"
        assert v.position == 68


def test_insertion_is_numbered_between_flanking_bases():
    # A1 T2 G3 ... -> insert C between A1 and T2.
    v = _single(REF[:1] + "C" + REF[1:])
    assert v.hgvs_c == "c.1_2insC"
    assert v.effect == "frameshift"


def test_insertion_repeating_previous_base_is_a_dup():
    # A1 T2 G3 G4 A5 -> an extra G in the GG run is c.4dup (3'-most G).
    v = _single(REF[:3] + "G" + REF[3:])
    assert v.hgvs_c == "c.4dup"


def test_in_frame_deletion():
    v = _single(REF[:3] + REF[6:])  # remove codon 2 (GAT)
    assert v.effect == "in_frame_deletion"
    assert v.hgvs_c.endswith("del")
