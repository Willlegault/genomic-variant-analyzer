"""Build a labeled missense-variant dataset from ClinVar for classifier training.

Source: NCBI ClinVar's tab-delimited release (`variant_summary.txt.gz`, ~450 MB),
which has one row per variant per genome assembly. Pipeline:

    1. Stream the file in chunks (it is too big to load comfortably at once).
    2. Keep GRCh38 single-nucleotide variants whose HGVS name ends in a
       missense protein change, e.g. "NM_007294.4(BRCA1):c.5123C>A (p.Ala1708Glu)".
    3. Keep only confident labels:
         1 = Pathogenic / Likely pathogenic
         0 = Benign / Likely benign
       Everything else (VUS, conflicting, risk factor, ...) is dropped, as are
       records with no review criteria behind them.
    4. Collapse duplicates: several nucleotide changes can produce the same
       protein change. Keep one row per (gene, protein change); drop it entirely
       if those rows disagree on the label.
    5. Assign each *gene* to train / val / test with a stable hash. Splitting by
       gene (not by variant) stops the model from scoring well just by learning
       "variants in gene X are usually pathogenic".

Usage (from backend/):
    venv/Scripts/python ml/build_dataset.py            # Windows
    venv/bin/python ml/build_dataset.py                # macOS / Linux

Outputs:
    ml/data/clinvar_missense.parquet   the dataset (gitignored)
    ml/reports/dataset_stats.json      counts and balance per split (committed)
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


_URL = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"

_ML_DIR = Path(__file__).resolve().parent
_RAW_PATH = _ML_DIR / "data" / "raw" / "variant_summary.txt.gz"
_OUT_PATH = _ML_DIR / "data" / "clinvar_missense.parquet"
_STATS_PATH = _ML_DIR / "reports" / "dataset_stats.json"

_COLUMNS = [
    "VariationID",
    "Type",
    "Name",
    "ClinicalSignificance",
    "ReviewStatus",
    "NumberSubmitters",
    "Assembly",
    "Chromosome",
    "PositionVCF",
    "ReferenceAlleleVCF",
    "AlternateAlleleVCF",
]

_LABELS = {
    "Pathogenic": 1,
    "Likely pathogenic": 1,
    "Pathogenic/Likely pathogenic": 1,
    "Benign": 0,
    "Likely benign": 0,
    "Benign/Likely benign": 0,
}

# ClinVar's "star" levels 1-4. Lower levels have no stated evidence criteria.
_TRUSTED_REVIEW = {
    "criteria provided, single submitter": 1,
    "criteria provided, multiple submitters, no conflicts": 2,
    "reviewed by expert panel": 3,
    "practice guideline": 4,
}

# "NM_007294.4(BRCA1):c.5123C>A (p.Ala1708Glu)"
_NAME_RE = re.compile(
    r"^(?P<transcript>NM_\d+\.\d+)\((?P<gene>[^)]+)\):(?P<hgvs_c>c\.\S+) "
    r"\(p\.(?P<ref_aa>[A-Z][a-z]{2})(?P<protein_pos>\d+)(?P<alt_aa>[A-Z][a-z]{2})\)$"
)

_STANDARD_AA = {
    "Ala", "Arg", "Asn", "Asp", "Cys", "Gln", "Glu", "Gly", "His", "Ile",
    "Leu", "Lys", "Met", "Phe", "Pro", "Ser", "Thr", "Trp", "Tyr", "Val",
}

_SPLITS = (("train", 70), ("val", 85), ("test", 100))  # cumulative % of genes


def _download_if_missing() -> None:
    if _RAW_PATH.exists():
        return
    _RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {_URL} (~450 MB)...")
    tmp = _RAW_PATH.with_suffix(".part")
    urllib.request.urlretrieve(_URL, tmp)
    tmp.rename(_RAW_PATH)


def _filter_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    chunk = chunk[
        (chunk["Assembly"] == "GRCh38")
        & (chunk["Type"] == "single nucleotide variant")
        & chunk["ClinicalSignificance"].isin(_LABELS)
        & chunk["ReviewStatus"].isin(_TRUSTED_REVIEW)
    ]
    parsed = chunk["Name"].str.extract(_NAME_RE)
    keep = (
        parsed["ref_aa"].isin(_STANDARD_AA)
        & parsed["alt_aa"].isin(_STANDARD_AA)
        & (parsed["ref_aa"] != parsed["alt_aa"])
    )
    out = pd.concat([chunk[keep], parsed[keep]], axis=1)
    out["label"] = out["ClinicalSignificance"].map(_LABELS)
    out["review_stars"] = out["ReviewStatus"].map(_TRUSTED_REVIEW)
    return out


def _gene_split(gene: str) -> str:
    bucket = int(hashlib.md5(gene.encode()).hexdigest(), 16) % 100
    for name, upper in _SPLITS:
        if bucket < upper:
            return name
    raise AssertionError("unreachable")


def _collapse_protein_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    key = ["gene", "ref_aa", "protein_pos", "alt_aa"]
    n_labels = df.groupby(key)["label"].transform("nunique")
    conflicting = df[n_labels > 1].drop_duplicates(key)
    # Prefer the best-reviewed record when several agree.
    df = (
        df[n_labels == 1]
        .sort_values("review_stars", ascending=False)
        .drop_duplicates(key)
    )
    return df, len(conflicting)


def _summarize(df: pd.DataFrame, raw_rows: int, conflicts: int) -> dict:
    per_split = {}
    for split, group in df.groupby("split"):
        per_split[split] = {
            "variants": len(group),
            "genes": group["gene"].nunique(),
            "pathogenic": int(group["label"].sum()),
            "benign": int((group["label"] == 0).sum()),
            "pathogenic_fraction": round(group["label"].mean(), 3),
        }
    top_genes = df["gene"].value_counts().head(10)
    return {
        "source": _URL,
        "source_file_modified": datetime.fromtimestamp(
            _RAW_PATH.stat().st_mtime, tz=timezone.utc
        ).date().isoformat(),
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows_after_filters": raw_rows,
        "protein_changes_dropped_for_label_conflict": conflicts,
        "variants": len(df),
        "genes": df["gene"].nunique(),
        "splits": per_split,
        "top_genes": {gene: int(n) for gene, n in top_genes.items()},
    }


def build() -> dict:
    _download_if_missing()

    reader = pd.read_csv(
        _RAW_PATH,
        sep="\t",
        usecols=_COLUMNS,
        dtype=str,
        chunksize=500_000,
    )
    parts = []
    for i, chunk in enumerate(reader, start=1):
        parts.append(_filter_chunk(chunk))
        print(f"  chunk {i}: kept {sum(len(p) for p in parts):,} rows so far")
    df = pd.concat(parts, ignore_index=True).drop_duplicates("VariationID")
    raw_rows = len(df)

    df, conflicts = _collapse_protein_duplicates(df)
    df["protein_pos"] = df["protein_pos"].astype(int)
    df["split"] = df["gene"].map(_gene_split)

    df = df.rename(
        columns={
            "VariationID": "variation_id",
            "ClinicalSignificance": "clinical_significance",
            "ReviewStatus": "review_status",
            "NumberSubmitters": "num_submitters",
            "Chromosome": "chrom",
            "PositionVCF": "pos",
            "ReferenceAlleleVCF": "ref",
            "AlternateAlleleVCF": "alt",
        }
    )[
        [
            "variation_id", "gene", "transcript", "hgvs_c",
            "ref_aa", "protein_pos", "alt_aa",
            "chrom", "pos", "ref", "alt",
            "clinical_significance", "review_status", "review_stars",
            "num_submitters", "label", "split",
        ]
    ].sort_values(["gene", "protein_pos"], ignore_index=True)

    _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_OUT_PATH, index=False)

    stats = _summarize(df, raw_rows, conflicts)
    _STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATS_PATH.write_text(json.dumps(stats, indent=2) + "\n")
    return stats


if __name__ == "__main__":
    summary = build()
    print(json.dumps(summary, indent=2))
