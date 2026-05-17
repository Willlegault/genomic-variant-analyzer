"use client";

import { useEffect, useState } from "react";
import { listReferences, analyze, ApiError } from "../lib/api";
import type { AnalysisResponse, ReferenceMeta } from "../lib/types";

interface Props {
  onResult: (result: AnalysisResponse) => void;
}

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
    // BRCA1 CDS head with the AG at positions 68-69 deleted — the
    // Ashkenazi-founder frameshift c.68_69delAG. Useful as a one-click demo.
    setSequence(
      "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCTATGCAGAAAATCTTAGTGTCCCATCTGTCTGGAGTTGATCAAGGAACCTGTCTCCACAAAGTGTGACCACATATTTTGCAAATTTTGCATGCTGAAACTTCTCAACCAGAAGAAAGGGCCTTCACAGTGTCCTTTATGT",
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        Paste a coding DNA sequence (A/T/C/G only) that matches the chosen
        reference region. The app performs a global alignment, reports variant
        calls in HGVS-like syntax, looks up ClinVar (unless skipped), and
        explains the biological consequence in plain language.
      </p>
      <div className="flex flex-col gap-2">
        <label htmlFor="reference" className="text-sm font-medium">
          Reference sequence
        </label>
        <select
          id="reference"
          value={referenceId}
          onChange={(e) => setReferenceId(e.target.value)}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-black"
          disabled={references.length === 0}
        >
          {references.map((r) => (
            <option key={r.id} value={r.id}>
              {r.gene} — {r.description}
            </option>
          ))}
        </select>
        {reference ? (
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            {reference.clinical_context} (Source: {reference.source}, length{" "}
            {reference.length} bp)
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <label htmlFor="sequence" className="text-sm font-medium">
            Query DNA sequence
          </label>
          <button
            type="button"
            onClick={loadFounderExample}
            className="text-xs text-blue-600 hover:underline dark:text-blue-400"
          >
            Load demo: BRCA1 founder frameshift (c.68_69delAG)
          </button>
        </div>
        <textarea
          id="sequence"
          value={sequence}
          onChange={(e) => setSequence(e.target.value)}
          placeholder="Paste an A/T/C/G sequence — must match the reference region (no spaces)."
          spellCheck={false}
          className="min-h-32 rounded-md border border-zinc-300 bg-white px-3 py-3 font-mono text-sm leading-relaxed text-black"
        />
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Whitespace is stripped automatically. {sequence.replace(/\s+/g, "").length} bp.
        </p>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={skipClinvar}
          onChange={(e) => setSkipClinvar(e.target.checked)}
        />
        Skip ClinVar lookup (faster). When enabled, the app will not fetch
        ClinVar records and pathogenicity will be shown as "Not in ClinVar".
      </label>

      {error ? (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={loading || !sequence.trim() || !referenceId}
        className="self-start rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-zinc-400"
      >
        {loading ? "Analyzing…" : "Analyze sequence"}
      </button>
    </form>
  );
}
