# Genomic Variant Analyzer

A full-stack tool for detecting and biologically interpreting DNA variants. Paste
a DNA sequence, pick a reference CDS, and the app aligns the two sequences,
classifies each variant by coding consequence (synonymous / missense / nonsense
/ frameshift / in-frame indel), looks up pathogenicity in ClinVar, and renders a
plain-language explanation suitable for a biology-literate reader.

The differentiator is the **biological reasoning layer** — the project is
intentionally bio-deep rather than just a CRUD demo on top of a famous-sounding
API.

## Stack

| Layer        | Tech                                                               |
| ------------ | ------------------------------------------------------------------ |
| Frontend     | Next.js 16 (App Router), React 19, TypeScript, Tailwind 4          |
| Visualization| Recharts (pathogenicity pie + coding-consequence bar)              |
| Backend      | Python 3.13 + Flask                                                |
| Bio          | Biopython (`Bio.Align.PairwiseAligner`, `Bio.Seq`)                 |
| External APIs| NCBI ClinVar via E-utilities (`esearch` + `esummary`)              |
| Persistence  | Supabase (optional — analysis history)                             |
| Deployment   | Vercel (frontend) + Railway (Flask)                                |

## Project layout

```
backend/
    app.py              Flask routes (/api/health, /api/references, /api/analyze, /api/history)
    references.py       Built-in reference CDS fragments + metadata (currently BRCA1)
    variants.py         Alignment + variant detection + coding-consequence classification
    clinvar.py          ClinVar lookup with TTL cache, timeouts, soft error handling
    explanations.py     Per-variant biological explanation copy
    supabase_client.py  Optional history persistence — no-ops when env unset
    schema.sql          Supabase table definition
    requirements.txt
    .env.example

frontend/
    app/
        page.tsx                  Main analysis page
        history/page.tsx          Saved-analyses list
        layout.tsx                Root layout (Geist font, dark mode)
        globals.css               Tailwind 4 entry
        components/
            SequenceForm.tsx      Reference picker + DNA textarea + submit
            Results.tsx           Header + charts + variant list
            VariantCard.tsx       One variant: HGVS, codon delta, ClinVar link, explanation
            Charts.tsx            Recharts pie (pathogenicity) and bar (effect)
        lib/
            types.ts              Shared types
            api.ts                Fetch wrappers
            style.ts              Color/label maps
```

## Biology layer — what's actually implemented

### Variant detection (`backend/variants.py`)
1. Pairwise global alignment (`PairwiseAligner`) of query against reference.
2. Walk the alignment to emit raw events: substitution, insertion, deletion.
   Consecutive gaps collapse into a single indel event.
3. For each event:
   - **Substitution** → look up the containing codon, translate ref vs alt,
     classify as `synonymous` / `missense` / `nonsense`.
   - **Insertion / deletion** → classify as `frameshift` if length is not a
     multiple of 3, otherwise `in_frame_insertion` / `in_frame_deletion`.
4. Emit HGVS-style coding nomenclature (`c.123A>G`, `c.66_67delAG`,
   `c.7_8insCCC`) and protein nomenclature (`p.Asp2Asn`) for substitutions.

### Caveats (worth knowing)

- **Left-aligned indels**: when the same indel could be represented at multiple
  equivalent positions inside a tandem repeat (e.g. `AGAG`), the aligner picks
  the leftmost. HGVS prefers the rightmost (the "3' rule"). For demos this is
  cosmetic — the call itself is correct, the position is the leftmost
  equivalent.
- **No MNV combining**: three adjacent SNPs that together form a stop codon
  are reported as three separate missense calls, not a single nonsense call.
- **HGVS positions are reference-fragment-relative**, not transcript-relative.
  Sufficient for ClinVar text search and human-readable display; not a
  substitute for a real HGVS validator.

### Reference

Currently a single built-in reference: the first 192 bp of `BRCA1` CDS
(`NM_007294.4`). The fragment includes the M1 start codon and contains the
Ashkenazi-founder frameshift `c.68_69delAG` (historically "185delAG"), which
the form provides as a one-click demo.

### ClinVar (`backend/clinvar.py`)

`esearch` against `db=clinvar` with `<gene>[gene] <hgvs_c> <hgvs_p>`, then
`esummary` on the top 20 hits, keeping only the record whose title names this
exact gene and variant. Pathogenicity is read from
`germline_classification.description` (current API) with fallback to
`clinical_significance.description` (legacy shape). Free-text labels are
bucketed into `pathogenic / likely_pathogenic / uncertain / conflicting /
likely_benign / benign / other / unknown` for visualization. A 1-hour TTL
cache prevents duplicate lookups within a session; failed lookups are not
cached, so a transient error doesn't stick.

NCBI allows 3 E-utilities requests per second (10 with an API key), and each
lookup makes two. Requests are spaced to stay under that limit, and an HTTP 429
is retried with backoff (each wait capped at 5 s). Set `NCBI_API_KEY` (free
from your NCBI account settings) to make multi-variant analyses about three
times faster.

Because an analysis runs inside a single HTTP request, ClinVar is checked for at
most 12 variants and for at most 20 seconds per analysis (`MAX_CLINVAR_LOOKUPS`
and `CLINVAR_TIME_BUDGET` in `app.py`). Variants past either limit are still
detected and explained, and are marked `not_checked` with the reason.

### Explanation layer (`backend/explanations.py`)

Each variant gets a `headline` + `body` written for a biology-literate reader,
plus context flags: BRCA1 truncating variants get a tumour-suppressor LOF note;
genes whose symbol starts with `CYP` get a pharmacogenomics note.

## Machine learning (`backend/ml/`)

The goal is a model that predicts whether a missense variant is pathogenic,
including for variants ClinVar has never classified.

### Dataset (`build_dataset.py`)

Streams ClinVar's `variant_summary.txt.gz` and keeps GRCh38 single-nucleotide
missense variants with a confident label (Pathogenic/Likely pathogenic = 1,
Benign/Likely benign = 0) and at least one review star, one row per protein
change: **200,957 variants across 15,281 genes**. Genes are hashed into
train/val/test (70/15/15), so the test set contains only genes the model never
saw. Counts are in `ml/reports/dataset_stats.json`.

### Baseline model (`features.py`, `train_baseline.py`)

51 features that describe only the amino-acid swap: BLOSUM62 score, changes in
hydropathy, side-chain volume, charge, polarity, and aromaticity, which residues
are involved (one-hot), and position in the protein. No feature identifies the
gene. Logistic regression on standardized features; `C` is chosen on the
validation genes.

Results on the **31,008 test variants from 2,228 unseen genes** (31% pathogenic):

| Method | ROC-AUC | PR-AUC |
| --- | --- | --- |
| Base-rate guess | 0.500 | 0.313 |
| BLOSUM62 alone (no training) | 0.675 | 0.444 |
| **Logistic regression baseline** | **0.739** | **0.557** |

- **What it learned.** A worse BLOSUM62 score is the strongest pathogenic signal.
  Losing a cysteine, glycine, or aromatic residue, or introducing a proline,
  also pushes toward pathogenic. Later positions lean benign, likely in part
  because very long proteins (e.g. TTN) carry many benign variants.
- **Calibration.** Predicted probabilities track observed rates up to ~0.7; above
  that the model is overconfident (e.g. 0.84 predicted vs 0.75 observed).
- **Why the gene split matters.** On a random variant split the same model scores
  ROC-AUC 0.755; adding a per-gene pathogenic-rate feature inflates that to
  **0.937** (PR-AUC 0.884), even though it learns nothing that transfers to a new
  gene.

Full numbers, including the calibration table and feature weights, are in
`ml/reports/baseline_metrics.json`. Published predictors that use evolutionary
conservation and protein structure (such as AlphaMissense) score much higher;
this baseline is the reference point the next features have to beat.

```bash
cd backend
pip install -r requirements-ml.txt
python ml/build_dataset.py     # ~450 MB download the first time, then ~40 s
python ml/train_baseline.py    # ~10 s; model saved to ml/data/models/ (gitignored)
```

## Running locally

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # optional: fill in SUPABASE_URL/KEY for history
python3 app.py             # serves on :5001
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                # serves on :3000
```

Visit `http://localhost:3000`, click "Load demo · 185delAG", then "Analyze
sequence". You'll get one detected variant (`c.68_69del`, frameshift), matched to
ClinVar record 17662 (Pathogenic), with charts and an explanation card.

### Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

GitHub Actions (`.github/workflows/ci.yml`) runs these tests, checks the gunicorn
config, and lints, type-checks, and builds the frontend on every pull request.

## Deployment

### Frontend → Vercel

Connect the repo, set the project root to `frontend/`, and add the env var
`NEXT_PUBLIC_API_URL` pointing at the Railway backend URL.

### Backend → Railway

- Service root: `backend/`
- Build: `pip install -r requirements.txt` (Python version from `.python-version`)
- Start: `gunicorn app:app`, as in the `Procfile`. Bind address, worker
  threads, and a 60 s timeout come from `gunicorn.conf.py`, which gunicorn
  loads automatically.
- Env vars: `FRONTEND_ORIGIN` (the Vercel URL), `NCBI_EMAIL`, and optionally
  `NCBI_API_KEY` and `SUPABASE_URL` + `SUPABASE_KEY`.
- Check it's up: `GET /api/health`.

### Supabase (optional)

Create a project, paste `backend/schema.sql` into the SQL editor, and copy the
project URL + anon key into the backend's env vars. With these unset the app
runs fine — history is just disabled.

## API

### `GET /api/health`
```json
{ "ok": true, "supabase_enabled": false, "ncbi_email_set": false }
```

### `GET /api/references`
Lists built-in references with metadata.

### `POST /api/analyze`
```json
{
  "sequence": "ATGGAT...",
  "reference_id": "BRCA1",
  "skip_clinvar": false
}
```
Returns `{ reference, query, variants, summary, analysis_id? }`.

### `GET /api/history`
Returns `{ enabled: bool, analyses: [...] }`.
