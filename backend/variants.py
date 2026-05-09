"""Variant detection and classification.

Aligns a query DNA sequence against a reference CDS fragment using
Bio.Align.PairwiseAligner (the modern replacement for pairwise2), walks the
alignment to emit raw substitution / insertion / deletion events, and classifies
each event into a coding consequence:

    - synonymous / missense / nonsense for substitutions
    - frameshift / in_frame_insertion / in_frame_deletion for indels

HGVS-style nomenclature is approximate (1-based positions on the supplied
reference, not on the genomic transcript) — sufficient for ClinVar text search
and for human-readable display, but not a substitute for a real HGVS validator.
"""

from dataclasses import asdict, dataclass, field
from typing import Literal

from Bio.Align import PairwiseAligner
from Bio.Seq import Seq


VariantType = Literal["snp", "insertion", "deletion"]
Effect = Literal[
    "synonymous",
    "missense",
    "nonsense",
    "frameshift",
    "in_frame_insertion",
    "in_frame_deletion",
    "unknown",
]


@dataclass
class Variant:
    type: VariantType
    effect: Effect
    position: int  # 1-based position in reference (start of event)
    ref_allele: str
    alt_allele: str
    hgvs_c: str
    hgvs_p: str | None = None
    codon_number: int | None = None  # 1-based codon index in reference
    ref_codon: str | None = None
    alt_codon: str | None = None
    ref_aa: str | None = None
    alt_aa: str | None = None
    notes: list[str] = field(default_factory=list)


_AA_THREE = {
    "A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys",
    "E": "Glu", "Q": "Gln", "G": "Gly", "H": "His", "I": "Ile",
    "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe", "P": "Pro",
    "S": "Ser", "T": "Thr", "W": "Trp", "Y": "Tyr", "V": "Val",
    "*": "Ter",
}


def _three_letter(aa: str) -> str:
    return _AA_THREE.get(aa, aa)


def _build_aligner() -> PairwiseAligner:
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -0.5
    return aligner


def _align(reference: str, query: str):
    aligner = _build_aligner()
    alignments = aligner.align(reference, query)
    return alignments[0]


def _aligned_strings(alignment) -> tuple[str, str]:
    """Return (reference_aligned, query_aligned) gap-padded strings."""
    return str(alignment[0]), str(alignment[1])


def _walk_alignment(ref_aligned: str, query_aligned: str) -> list[dict]:
    events: list[dict] = []
    ref_pos = 0  # 0-indexed position in original reference
    i = 0
    n = len(ref_aligned)

    while i < n:
        r = ref_aligned[i]
        q = query_aligned[i]

        if r == q:
            ref_pos += 1
            i += 1
            continue

        if r != "-" and q != "-":
            events.append({
                "type": "snp",
                "ref_pos": ref_pos,
                "ref": r,
                "alt": q,
            })
            ref_pos += 1
            i += 1
            continue

        if r == "-":
            inserted: list[str] = []
            while i < n and ref_aligned[i] == "-":
                inserted.append(query_aligned[i])
                i += 1
            events.append({
                "type": "insertion",
                "ref_pos": ref_pos,  # insertion happens *before* this 0-idx position
                "ref": "",
                "alt": "".join(inserted),
            })
            continue

        # q == "-"
        deleted: list[str] = []
        start = ref_pos
        while i < n and query_aligned[i] == "-":
            deleted.append(ref_aligned[i])
            ref_pos += 1
            i += 1
        events.append({
            "type": "deletion",
            "ref_pos": start,
            "ref": "".join(deleted),
            "alt": "",
        })

    return events


def _classify_snp(reference: str, ref_pos: int, alt: str, frame_offset: int) -> dict:
    """Codon-aware classification of a single substitution.

    ref_pos is 0-indexed.
    """
    cds_pos = ref_pos - frame_offset
    if cds_pos < 0:
        return {"effect": "unknown", "notes": ["substitution falls outside reading frame"]}

    codon_idx = cds_pos // 3
    pos_in_codon = cds_pos % 3
    codon_start = frame_offset + codon_idx * 3

    if codon_start + 3 > len(reference):
        return {"effect": "unknown", "notes": ["incomplete codon at end of reference"]}

    ref_codon = reference[codon_start:codon_start + 3]
    alt_codon = (
        ref_codon[:pos_in_codon] + alt + ref_codon[pos_in_codon + 1:]
    )

    ref_aa = str(Seq(ref_codon).translate())
    alt_aa = str(Seq(alt_codon).translate())

    if ref_aa == alt_aa:
        effect: Effect = "synonymous"
    elif alt_aa == "*":
        effect = "nonsense"
    else:
        effect = "missense"

    return {
        "effect": effect,
        "codon_number": codon_idx + 1,
        "ref_codon": ref_codon,
        "alt_codon": alt_codon,
        "ref_aa": ref_aa,
        "alt_aa": alt_aa,
    }


def _hgvs_p_for_snp(info: dict) -> str | None:
    if info.get("effect") in {"synonymous", "missense", "nonsense"}:
        ref_aa = info["ref_aa"]
        alt_aa = info["alt_aa"]
        codon = info["codon_number"]
        if info["effect"] == "synonymous":
            return f"p.{_three_letter(ref_aa)}{codon}="
        return f"p.{_three_letter(ref_aa)}{codon}{_three_letter(alt_aa)}"
    return None


def _classify_event(reference: str, event: dict, frame_offset: int) -> Variant:
    etype = event["type"]
    ref_pos_0 = event["ref_pos"]
    pos_1 = ref_pos_0 + 1

    if etype == "snp":
        info = _classify_snp(reference, ref_pos_0, event["alt"], frame_offset)
        return Variant(
            type="snp",
            effect=info.get("effect", "unknown"),
            position=pos_1,
            ref_allele=event["ref"],
            alt_allele=event["alt"],
            hgvs_c=f"c.{pos_1}{event['ref']}>{event['alt']}",
            hgvs_p=_hgvs_p_for_snp(info),
            codon_number=info.get("codon_number"),
            ref_codon=info.get("ref_codon"),
            alt_codon=info.get("alt_codon"),
            ref_aa=info.get("ref_aa"),
            alt_aa=info.get("alt_aa"),
            notes=info.get("notes", []),
        )

    if etype == "insertion":
        alt = event["alt"]
        effect: Effect = "frameshift" if len(alt) % 3 != 0 else "in_frame_insertion"
        # HGVS insertion syntax: c.{pos}_{pos+1}ins{bases}
        hgvs_c = f"c.{pos_1}_{pos_1 + 1}ins{alt}"
        return Variant(
            type="insertion",
            effect=effect,
            position=pos_1,
            ref_allele="",
            alt_allele=alt,
            hgvs_c=hgvs_c,
            notes=[f"{len(alt)} bp inserted"],
        )

    # deletion
    ref = event["ref"]
    effect = "frameshift" if len(ref) % 3 != 0 else "in_frame_deletion"
    end_1 = pos_1 + len(ref) - 1
    hgvs_c = f"c.{pos_1}del{ref}" if len(ref) == 1 else f"c.{pos_1}_{end_1}del{ref}"
    return Variant(
        type="deletion",
        effect=effect,
        position=pos_1,
        ref_allele=ref,
        alt_allele="",
        hgvs_c=hgvs_c,
        notes=[f"{len(ref)} bp deleted"],
    )


def detect_variants(reference: str, query: str, frame_offset: int = 0) -> list[Variant]:
    """Return a list of classified variants between query and reference.

    An empty list means the query matches the reference exactly within the
    aligner's scoring model.
    """
    if reference == query:
        return []

    alignment = _align(reference, query)
    ref_aligned, query_aligned = _aligned_strings(alignment)
    events = _walk_alignment(ref_aligned, query_aligned)
    return [_classify_event(reference, e, frame_offset) for e in events]


def variants_to_dicts(variants: list[Variant]) -> list[dict]:
    return [asdict(v) for v in variants]


def summarize(variants: list[Variant]) -> dict:
    """Aggregate counts useful for the visualization layer."""
    by_type: dict[str, int] = {}
    by_effect: dict[str, int] = {}
    for v in variants:
        by_type[v.type] = by_type.get(v.type, 0) + 1
        by_effect[v.effect] = by_effect.get(v.effect, 0) + 1
    return {
        "total": len(variants),
        "by_type": by_type,
        "by_effect": by_effect,
    }
