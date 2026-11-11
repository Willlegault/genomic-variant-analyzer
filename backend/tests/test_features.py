import pytest

from ml.features import FEATURE_NAMES, featurize, to_one_letter


def _named(ref, alt, pos=100):
    return dict(zip(FEATURE_NAMES, featurize(ref, alt, pos)))


def test_vector_matches_feature_names():
    assert len(featurize("Cys", "Gly", 61)) == len(FEATURE_NAMES)


def test_brca1_c61g():
    f = _named("Cys", "Gly", 61)
    assert f["blosum62"] == -3.0
    assert f["ref_C"] == 1.0 and f["alt_G"] == 1.0
    assert sum(f[f"ref_{aa}"] for aa in "ACDEFGHIKLMNPQRSTVWY") == 1.0


def test_charge_flip():
    f = _named("Asp", "Lys")
    assert f["charge_delta"] == 2.0
    assert f["charge_flip"] == 1.0
    assert _named("Asp", "Glu")["charge_flip"] == 0.0


def test_conservative_change_scores_higher_than_radical_one():
    assert _named("Ile", "Val")["blosum62"] > _named("Trp", "Gly")["blosum62"]


def test_one_and_three_letter_codes_agree():
    assert featurize("C", "G", 61) == featurize("Cys", "Gly", 61)


def test_rejects_non_standard_residue():
    with pytest.raises(ValueError):
        to_one_letter("Ter")
