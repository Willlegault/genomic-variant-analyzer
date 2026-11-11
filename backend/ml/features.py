"""Per-variant features for the missense pathogenicity baseline.

Everything here describes the amino-acid swap itself: how chemically different
the two residues are, which residues are involved, and roughly where in the
protein it happens. Nothing identifies the gene, so the model cannot score well
by memorising "variants in gene X are pathogenic" (see build_dataset.py on why
the dataset is split by gene).

Pure Python + Biopython, so the web backend can import it to score variants
without pandas or scikit-learn.
"""

from __future__ import annotations

import math

from Bio.Align import substitution_matrices

AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"

THREE_TO_ONE = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
}

# Kyte & Doolittle (1982) hydropathy: positive = hydrophobic.
HYDROPATHY = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

# Side-chain volume in cubic angstroms (Zamyatnin 1972).
VOLUME = {
    "A": 88.6, "R": 173.4, "N": 114.1, "D": 111.1, "C": 108.5, "Q": 143.8,
    "E": 138.4, "G": 60.1, "H": 153.2, "I": 166.7, "L": 166.7, "K": 168.6,
    "M": 162.9, "F": 189.9, "P": 112.7, "S": 89.0, "T": 116.1, "W": 227.8,
    "Y": 193.6, "V": 140.0,
}

# Net side-chain charge at physiological pH (His treated as neutral).
CHARGE = {"D": -1, "E": -1, "K": 1, "R": 1}

POLAR = set("RNDQEHKSTY")
AROMATIC = set("FWYH")

_BLOSUM62 = substitution_matrices.load("BLOSUM62")

FEATURE_NAMES: list[str] = [
    "blosum62",
    "hydropathy_ref",
    "hydropathy_delta",
    "hydropathy_abs_delta",
    "volume_delta",
    "volume_abs_delta",
    "charge_delta",
    "charge_flip",
    "polarity_change",
    "aromatic_change",
    "log_protein_pos",
    *[f"ref_{aa}" for aa in AMINO_ACIDS],
    *[f"alt_{aa}" for aa in AMINO_ACIDS],
]


def to_one_letter(aa: str) -> str:
    """Accept "Cys" or "C"; return "C". Raises ValueError for anything else."""
    one = THREE_TO_ONE.get(aa, aa)
    if one not in HYDROPATHY:
        raise ValueError(f"Not a standard amino acid: {aa!r}")
    return one


def featurize(ref_aa: str, alt_aa: str, protein_pos: int) -> list[float]:
    """Feature vector for one missense change, in FEATURE_NAMES order."""
    ref, alt = to_one_letter(ref_aa), to_one_letter(alt_aa)
    charge_delta = CHARGE.get(alt, 0) - CHARGE.get(ref, 0)
    features = [
        float(_BLOSUM62[ref][alt]),
        HYDROPATHY[ref],
        HYDROPATHY[alt] - HYDROPATHY[ref],
        abs(HYDROPATHY[alt] - HYDROPATHY[ref]),
        VOLUME[alt] - VOLUME[ref],
        abs(VOLUME[alt] - VOLUME[ref]),
        float(charge_delta),
        float(abs(charge_delta) == 2),
        float((ref in POLAR) != (alt in POLAR)),
        float((ref in AROMATIC) != (alt in AROMATIC)),
        math.log1p(max(protein_pos, 0)),
    ]
    features += [float(ref == aa) for aa in AMINO_ACIDS]
    features += [float(alt == aa) for aa in AMINO_ACIDS]
    return features
