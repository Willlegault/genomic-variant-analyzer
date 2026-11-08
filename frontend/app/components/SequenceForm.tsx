"use client";

import { useEffect, useState } from "react";
import { listReferences, analyze, ApiError } from "../lib/api";
import type { AnalysisResponse, ReferenceMeta } from "../lib/types";

interface Props {
  onResult: (result: AnalysisResponse) => void;
}

const FIELD =
  "rounded-lg border border-line bg-panel-strong px-3 text-sm text-fg placeholder:text-muted/60 focus:border-accent focus:outline-none";

export function SequenceForm({ onResult }: Props) {
  const [references, setReferences] = useState<ReferenceMeta[]>([]);
  const [referenceId, setReferenceId] = useState<string>("");
  const [sequence, setSequence] = useState("");
  const [skipClinvar, setSkipClinvar] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listReferences()
      .then((r) => {
        setReferences(r.references);
        if (r.references[0]) setReferenceId(r.references[0].id);
      })
      .catch((e) => setError(`Could not load references: ${(e as Error).message}`));
  }, []);

  const reference = references.find((r) => r.id === referenceId);
  const length = sequence.replace(/\s+/g, "").length;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const cleaned = sequence.replace(/\s+/g, "").toUpperCase();
      const result = await analyze(cleaned, {
        reference_id: referenceId,
        skip_clinvar: skipClinvar,
      });
      onResult(result);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : (e as Error).message;
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function loadFounderExample() {
    // BRCA1 CDS head with one AG of the AGAG repeat at 66-69 deleted — the
    // Ashkenazi-founder frameshift c.68_69del (historically "185delAG").
    setSequence(
      "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCTATGCAGAAAATCTTAGTGTCCCATCTGTCTGGAGTTGATCAAGGAACCTGTCTCCACAAAGTGTGACCACATATTTTGCAAATTTTGCATGCTGAAACTTCTCAACCAGAAGAAAGGGCCTTCACAGTGTCCTTTATGT",
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <label htmlFor="reference" className="text-sm font-medium text-fg">
          Reference sequence
        </label>
        <select
          id="reference"
          value={referenceId}
          onChange={(e) => setReferenceId(e.target.value)}
          className={`${FIELD} py-2.5`}
          disabled={references.length === 0}
        >
          {references.map((r) => (
            <option key={r.id} value={r.id}>
              {r.gene} · first {r.length} bp of coding sequence
            </option>
          ))}
        </select>
        {reference ? (
          <details className="text-xs text-muted">
            <summary className="cursor-pointer select-none hover:text-fg">
              {reference.source} · about {reference.gene}
            </summary>
            <p className="mt-1.5 leading-relaxed">{reference.clinical_context}</p>
          </details>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label htmlFor="sequence" className="text-sm font-medium text-fg">
            Query DNA sequence
          </label>
          <button
            type="button"
            onClick={loadFounderExample}
            className="rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-xs font-medium text-accent transition hover:bg-accent/20"
          >
            Load demo · 185delAG
          </button>
        </div>
        <textarea
          id="sequence"
          value={sequence}
          onChange={(e) => setSequence(e.target.value)}
          placeholder="A, T, C, G only"
          spellCheck={false}
          className={`${FIELD} min-h-36 py-3 font-mono leading-relaxed tracking-wide break-all`}
        />
        <p className="text-xs text-muted">
          <span className="font-mono tabular-nums text-fg">{length}</span>
          {reference ? ` / ${reference.length}` : ""} bp · spaces ignored
        </p>
      </div>

      <label className="flex items-center gap-3 text-sm text-muted">
        <input
          type="checkbox"
          checked={skipClinvar}
          onChange={(e) => setSkipClinvar(e.target.checked)}
          className="h-4 w-4 accent-[var(--accent)]"
        />
        Skip ClinVar (faster)
      </label>

      {error ? (
        <div className="rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={loading || !sequence.trim() || !referenceId}
        className="self-start rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-muted"
      >
        {loading ? "Analyzing…" : "Analyze sequence"}
      </button>
    </form>
  );
}
