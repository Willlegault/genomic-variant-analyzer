"""Flask entry point.

Thin route layer over:
    - references.py      reference sequences + metadata
    - variants.py        alignment + variant classification
    - clinvar.py         ClinVar pathogenicity lookup
    - explanations.py    biological explanation copy
    - supabase_client.py history persistence (optional)

Endpoints:
    GET  /api/health            liveness + which integrations are configured
    GET  /api/references        list available reference sequences
    POST /api/analyze           run the variant pipeline on a query sequence
    GET  /api/history           recent analyses (Supabase-backed; [] if disabled)
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

import clinvar
import supabase_client
from explanations import explain_variant
from references import get_reference, list_references
from variants import detect_variants, summarize, variants_to_dicts


load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("variant-analyzer")

MAX_SEQUENCE_LENGTH = 10_000  # guard against pathological inputs

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.environ.get("FRONTEND_ORIGIN", "*")}})


def _validate_sequence(seq: str) -> str | None:
    """Return an error message if the sequence is invalid, else None."""
    if not seq:
        return "No sequence provided."
    if len(seq) > MAX_SEQUENCE_LENGTH:
        return f"Sequence too long: {len(seq)} bp (max {MAX_SEQUENCE_LENGTH})."
    invalid = set(seq) - set("ATCG")
    if invalid:
        return f"Invalid bases in sequence: {sorted(invalid)}. Only A, T, C, G allowed."
    return None


@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "supabase_enabled": supabase_client.is_enabled(),
        "ncbi_email_set": bool(os.environ.get("NCBI_EMAIL")),
    })


@app.get("/api/references")
def references_endpoint():
    return jsonify({"references": list_references()})


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    sequence = (payload.get("sequence") or "").upper().strip()
    reference_id = payload.get("reference_id")
    skip_clinvar = bool(payload.get("skip_clinvar", False))

    error = _validate_sequence(sequence)
    if error:
        return jsonify({"error": error}), 400

    try:
        reference = get_reference(reference_id)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 400

    variants = detect_variants(reference.sequence, sequence, frame_offset=reference.frame_offset)
    variant_dicts = variants_to_dicts(variants)

    # Attach ClinVar lookups + biological explanations.
    for v in variant_dicts:
        v["explanation"] = explain_variant(v, reference)
        if skip_clinvar:
            v["clinvar"] = {"skipped": True}
            v["pathogenicity"] = "unknown"
            continue
        cv = clinvar.lookup(reference.gene, v["hgvs_c"], v.get("hgvs_p"))
        v["clinvar"] = cv
        v["pathogenicity"] = clinvar.normalize_classification(cv.get("classification"))

    summary = summarize(variants)
    summary["by_pathogenicity"] = _pathogenicity_breakdown(variant_dicts)

    response = {
        "reference": {
            "id": reference.id,
            "gene": reference.gene,
            "description": reference.description,
            "pathway": reference.pathway,
            "clinical_context": reference.clinical_context,
            "source": reference.source,
            "length": len(reference.sequence),
        },
        "query": {
            "length": len(sequence),
            "sequence": sequence,
        },
        "variants": variant_dicts,
        "summary": summary,
    }

    saved = supabase_client.save_analysis({
        "reference_id": reference.id,
        "gene": reference.gene,
        "query_sequence": sequence,
        "query_length": len(sequence),
        "variant_count": len(variant_dicts),
        "summary": summary,
        "variants": variant_dicts,
    })
    if saved and "id" in saved:
        response["analysis_id"] = saved["id"]

    return jsonify(response)


@app.get("/api/history")
def history():
    return jsonify({
        "enabled": supabase_client.is_enabled(),
        "analyses": supabase_client.list_analyses(limit=25),
    })


def _pathogenicity_breakdown(variants: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for v in variants:
        bucket = v.get("pathogenicity", "unknown")
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


if __name__ == "__main__":
    app.run(debug=True, port=5001)
