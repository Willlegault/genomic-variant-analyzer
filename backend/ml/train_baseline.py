"""Train and evaluate the baseline missense pathogenicity classifier.

Model: standardized features (features.py) -> logistic regression. The
regularization strength C is picked on the validation genes; the reported score
is on the test genes, which the model never saw.

Alongside the model this reports:
  - two reference points on the same test genes: guessing the base rate, and
    ranking by BLOSUM62 alone (a classic substitution score, no training);
  - a calibration table, because a "0.8" should mean ~80% of such variants are
    pathogenic if the score is ever shown to a user;
  - a leakage check: the same model on a random variant split, with and without
    a per-gene "how often is this gene pathogenic" feature, to show how much a
    careless split would inflate the numbers.

Usage (from backend/, after build_dataset.py):
    venv/Scripts/python ml/train_baseline.py      # Windows
    venv/bin/python ml/train_baseline.py          # macOS / Linux

Outputs:
    ml/data/models/baseline_logreg.joblib   trained pipeline (gitignored)
    ml/reports/baseline_metrics.json        metrics (committed)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import FEATURE_NAMES, featurize

_ML_DIR = Path(__file__).resolve().parent
_DATA_PATH = _ML_DIR / "data" / "clinvar_missense.parquet"
_MODEL_PATH = _ML_DIR / "data" / "models" / "baseline_logreg.joblib"
_METRICS_PATH = _ML_DIR / "reports" / "baseline_metrics.json"

_C_GRID = (0.001, 0.01, 0.1, 1.0, 10.0)
_SEED = 0


def _model(c: float):
    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=2000))


def _features(df: pd.DataFrame) -> np.ndarray:
    return np.array(
        [featurize(r, a, p) for r, a, p in zip(df["ref_aa"], df["alt_aa"], df["protein_pos"])]
    )


def _scores(y: np.ndarray, p: np.ndarray) -> dict:
    return {
        "roc_auc": round(float(roc_auc_score(y, p)), 4),
        "pr_auc": round(float(average_precision_score(y, p)), 4),
    }


def _calibration(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if mask.sum() == 0:
            continue
        rows.append({
            "bin": f"{lo:.1f}-{hi:.1f}",
            "variants": int(mask.sum()),
            "mean_predicted": round(float(p[mask].mean()), 3),
            "observed_pathogenic": round(float(y[mask].mean()), 3),
        })
    return rows


def _gene_prior(train: pd.DataFrame, other: pd.DataFrame, strength: float = 10.0) -> tuple:
    """Smoothed per-gene pathogenic rate from `train`, mapped onto both frames."""
    overall = train["label"].mean()
    stats = train.groupby("gene")["label"].agg(["sum", "count"])
    rate = (stats["sum"] + strength * overall) / (stats["count"] + strength)
    return (
        train["gene"].map(rate).fillna(overall).to_numpy(),
        other["gene"].map(rate).fillna(overall).to_numpy(),
    )


def _leakage_check(df: pd.DataFrame, X: np.ndarray, c: float) -> dict:
    """Same features on a random variant split, then with a gene-identity feature."""
    idx_train, idx_test = train_test_split(
        np.arange(len(df)), test_size=0.3, random_state=_SEED, stratify=df["label"]
    )
    y = df["label"].to_numpy()
    random_split = _model(c).fit(X[idx_train], y[idx_train])
    p_random = random_split.predict_proba(X[idx_test])[:, 1]

    prior_train, prior_test = _gene_prior(df.iloc[idx_train], df.iloc[idx_test])
    X_train_prior = np.column_stack([X[idx_train], prior_train])
    X_test_prior = np.column_stack([X[idx_test], prior_test])
    with_prior = _model(c).fit(X_train_prior, y[idx_train])
    p_prior = with_prior.predict_proba(X_test_prior)[:, 1]

    return {
        "random_split_same_features": _scores(y[idx_test], p_random),
        "random_split_plus_gene_prior": _scores(y[idx_test], p_prior),
        "note": (
            "Random splits put variants from the same gene in train and test. "
            "Adding a per-gene pathogenic-rate feature then lets the model look "
            "far better than it is on genes it has never seen."
        ),
    }


def train() -> dict:
    df = pd.read_parquet(_DATA_PATH)
    X = _features(df)
    y = df["label"].to_numpy()
    split = df["split"].to_numpy()
    tr, va, te = split == "train", split == "val", split == "test"

    sweep = []
    for c in _C_GRID:
        p_val = _model(c).fit(X[tr], y[tr]).predict_proba(X[va])[:, 1]
        sweep.append({"C": c, **_scores(y[va], p_val)})
    best_c = max(sweep, key=lambda s: s["pr_auc"])["C"]

    model = _model(best_c).fit(X[tr], y[tr])
    p_val = model.predict_proba(X[va])[:, 1]
    p_test = model.predict_proba(X[te])[:, 1]

    blosum = X[:, FEATURE_NAMES.index("blosum62")]
    prevalence = float(y[te].mean())

    coefs = model.named_steps["logisticregression"].coef_[0]
    ranked = sorted(zip(FEATURE_NAMES, coefs), key=lambda kv: kv[1])

    metrics = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": "StandardScaler + LogisticRegression",
        "features": len(FEATURE_NAMES),
        "C_sweep_on_val": sweep,
        "chosen_C": best_c,
        "val": _scores(y[va], p_val),
        "test": {
            **_scores(y[te], p_test),
            "brier": round(float(brier_score_loss(y[te], p_test)), 4),
            "variants": int(te.sum()),
            "genes": int(df.loc[te, "gene"].nunique()),
            "pathogenic_fraction": round(prevalence, 3),
        },
        "test_reference_points": {
            "base_rate_guess": {"roc_auc": 0.5, "pr_auc": round(prevalence, 4)},
            "blosum62_only": _scores(y[te], -blosum[te]),
        },
        "test_calibration": _calibration(y[te], p_test),
        "most_pathogenic_features": [
            {"feature": n, "weight": round(float(w), 3)} for n, w in reversed(ranked[-8:])
        ],
        "most_benign_features": [
            {"feature": n, "weight": round(float(w), 3)} for n, w in ranked[:8]
        ],
        "leakage_check": _leakage_check(df, X, best_c),
    }

    _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": model, "feature_names": FEATURE_NAMES}, _MODEL_PATH)
    _METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
