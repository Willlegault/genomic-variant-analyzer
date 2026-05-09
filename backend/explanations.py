"""Plain-language biological explanations per variant + reference.

This module is the project's biological-reasoning layer — the differentiator
described in the original scope. The explanations are written for a
biology-literate but non-clinician reader (recruiter, hiring manager, fellow
student), erring on the side of correctness over color.
"""

from __future__ import annotations

from references import Reference


_EFFECT_BLURBS: dict[str, dict[str, str]] = {
    "synonymous": {
        "headline": "Silent (synonymous) substitution",
        "body": (
            "The base change does not alter the encoded amino acid because the "
            "genetic code is degenerate. These are typically tolerated, though "
            "rare cases affect splicing, mRNA stability, or codon-usage-driven "
            "translation kinetics."
        ),
    },
    "missense": {
        "headline": "Missense substitution",
        "body": (
            "A single base change replaces one amino acid with another. The "
            "phenotypic consequence depends on how chemically different the two "
            "residues are, how conserved the position is across species, and "
            "where the residue sits in the folded protein (active site, "
            "interface, surface loop)."
        ),
    },
    "nonsense": {
        "headline": "Nonsense substitution (premature stop codon)",
        "body": (
            "The base change introduces a stop codon, truncating the protein. "
            "Truncated transcripts are usually degraded by nonsense-mediated "
            "decay, producing a loss-of-function allele. In tumour-suppressor "
            "genes like BRCA1, loss-of-function variants are the canonical "
            "pathogenic mechanism."
        ),
    },
    "frameshift": {
        "headline": "Frameshift indel",
        "body": (
            "An insertion or deletion whose length is not divisible by three "
            "shifts the downstream reading frame, scrambling every codon after "
            "the event and almost always producing a premature stop codon. "
            "Like nonsense variants, frameshifts in tumour-suppressor genes "
            "are typically loss-of-function and pathogenic."
        ),
    },
    "in_frame_insertion": {
        "headline": "In-frame insertion",
        "body": (
            "An insertion of a multiple of three bases adds whole amino acids "
            "without disturbing the downstream reading frame. The functional "
            "impact depends on whether the inserted residues fall in a "
            "structured domain, a flexible linker, or near a binding site."
        ),
    },
    "in_frame_deletion": {
        "headline": "In-frame deletion",
        "body": (
            "Deleting a multiple of three bases removes whole amino acids "
            "without shifting the reading frame downstream. The consequence "
            "depends on which residues are lost and whether they participate "
            "in folding, catalysis, or protein-protein interactions."
        ),
    },
    "unknown": {
        "headline": "Unclassified change",
        "body": (
            "The variant could not be placed in a coding context — it may "
            "fall outside the supplied reading frame or span an incomplete "
            "codon at the end of the reference fragment."
        ),
    },
}


def explain_effect(effect: str) -> dict:
    return _EFFECT_BLURBS.get(effect, _EFFECT_BLURBS["unknown"])


def cyp450_flag(gene: str) -> bool:
    """True when the gene belongs to the cytochrome P450 superfamily.

    CYP450 variants are flagged separately because they are clinically
    actionable in pharmacogenomics — they govern the metabolism of a large
    fraction of prescribed drugs.
    """
    return gene.upper().startswith("CYP")


def explain_variant(variant: dict, reference: Reference) -> dict:
    """Attach a structured `explanation` block to a variant dict."""
    blurb = explain_effect(variant.get("effect", "unknown"))
    notes: list[str] = []

    if cyp450_flag(reference.gene):
        notes.append(
            f"{reference.gene} is a cytochrome P450 enzyme — coding variants "
            "may alter drug metabolism (poor / intermediate / extensive / "
            "ultra-rapid metabolizer phenotypes)."
        )

    if reference.gene == "BRCA1" and variant.get("effect") in {"nonsense", "frameshift"}:
        notes.append(
            "BRCA1 is a tumour-suppressor gene; truncating variants in the "
            "coding sequence are the classic mechanism of pathogenicity in "
            "hereditary breast and ovarian cancer."
        )

    return {
        "headline": blurb["headline"],
        "body": blurb["body"],
        "context": notes,
        "gene": reference.gene,
        "pathway": reference.pathway,
    }
