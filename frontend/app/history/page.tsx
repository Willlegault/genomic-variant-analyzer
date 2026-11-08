"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, getHistory } from "../lib/api";
import { PATHOGENICITY_LABELS } from "../lib/style";
import type { AnalysisRecord } from "../lib/types";

export default function HistoryPage() {
  const [records, setRecords] = useState<AnalysisRecord[]>([]);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHistory()
      .then((r) => {
        setEnabled(r.enabled);
        setRecords(r.analyses);
      })
      .catch((e) => {
        const msg = e instanceof ApiError ? e.message : (e as Error).message;
        setError(msg);
      });
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-10 sm:px-8">
      <header className="glass flex flex-wrap items-center justify-between gap-3 p-6">
        <h1 className="text-2xl font-bold tracking-tight">Analysis history</h1>
        <Link
          href="/"
          className="rounded-full border border-line px-3 py-1 text-sm text-fg transition hover:border-accent hover:text-accent"
        >
          ← New analysis
        </Link>
      </header>

      {error ? (
        <div className="rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      {enabled === false ? (
        <div className="glass p-5 text-sm leading-relaxed text-muted">
          History is off. To turn it on, run{" "}
          <code className="font-mono text-fg">backend/schema.sql</code> in Supabase and set{" "}
          <code className="font-mono text-fg">SUPABASE_URL</code> and{" "}
          <code className="font-mono text-fg">SUPABASE_KEY</code> in{" "}
          <code className="font-mono text-fg">backend/.env</code>.
        </div>
      ) : null}

      {enabled && records.length === 0 ? (
        <p className="glass p-5 text-sm text-muted">No analyses yet.</p>
      ) : null}

      <ul className="flex flex-col gap-3">
        {records.map((r) => {
          const topPathogenicity = Object.entries(r.summary.by_pathogenicity).sort(
            ([, a], [, b]) => b - a,
          )[0];
          return (
            <li key={r.id} className="glass p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="font-mono text-sm font-semibold text-accent">{r.gene}</div>
                <time className="text-xs text-muted">
                  {new Date(r.created_at).toLocaleString()}
                </time>
              </div>
              <div className="mt-2 text-xs text-muted">
                {r.query_length} bp · {r.variant_count} variant
                {r.variant_count === 1 ? "" : "s"}
                {topPathogenicity
                  ? ` · mostly ${
                      PATHOGENICITY_LABELS[
                        topPathogenicity[0] as keyof typeof PATHOGENICITY_LABELS
                      ] ?? topPathogenicity[0]
                    } (${topPathogenicity[1]})`
                  : null}
              </div>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
