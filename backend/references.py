"""Built-in reference sequences with biological metadata.

Each reference is a coding-sequence (CDS) fragment whose first base is the first
base of a codon (frame 0), so codon-aware variant classification works without a
caller-supplied frame offset. Sources are cited per-entry for traceability.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Reference:
    id: str
    gene: str
    description: str
    pathway: str
    clinical_context: str
    source: str
    sequence: str
    frame_offset: int = 0


# BRCA1 — first 192 bp (64 codons) of the canonical CDS, NM_007294.4.
# Includes the M1 start codon. The Ashkenazi-founder frameshift c.68_69delAG
# (historically "185delAG") falls inside this window — deleting the AG at
# 1-based positions 68-69 — which makes this fragment a useful demo target for
# frameshift detection.
BRCA1_CDS_HEAD = (
    "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCTATGCAGAAA"
    "ATCTTAGAGTGTCCCATCTGTCTGGAGTTGATCAAGGAACCTGTCTCCACAAAGTGTGAC"
    "CACATATTTTGCAAATTTTGCATGCTGAAACTTCTCAACCAGAAGAAAGGGCCTTCACAG"
    "TGTCCTTTATGT"
)


REFERENCES: dict[str, Reference] = {
    "BRCA1": Reference(
        id="BRCA1",
        gene="BRCA1",
        description="Breast Cancer 1, DNA Repair Associated — first 192 bp of CDS (NM_007294.4)",
        pathway="Homologous recombination DNA repair",
        clinical_context=(
            "Germline pathogenic variants in BRCA1 confer substantially elevated "
            "lifetime risk of breast and ovarian cancer. The Ashkenazi-founder "
            "frameshift c.68_69delAG falls within this fragment."
        ),
        source="NCBI RefSeq NM_007294.4",
        sequence=BRCA1_CDS_HEAD,
        frame_offset=0,
    ),
}


DEFAULT_REFERENCE_ID = "BRCA1"


def get_reference(reference_id: str | None = None) -> Reference:
    key = reference_id or DEFAULT_REFERENCE_ID
    if key not in REFERENCES:
        raise KeyError(f"Unknown reference id: {key}")
    return REFERENCES[key]


def list_references() -> list[dict]:
    return [
        {
            "id": r.id,
            "gene": r.gene,
            "description": r.description,
            "pathway": r.pathway,
            "clinical_context": r.clinical_context,
            "source": r.source,
            "length": len(r.sequence),
        }
        for r in REFERENCES.values()
    ]
