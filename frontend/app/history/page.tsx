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
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Analysis history</h1>
        <Link
          href="/"
          className="text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          ← New analysis
        </Link>
      </header>

      {error ? (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      ) : null}

      {enabled === false ? (
        <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
          History persistence is disabled — set SUPABASE_URL and SUPABASE_KEY in{" "}
          <code className="font-mono">backend/.env</code> to enable it.
        </div>
      ) : null}

      {enabled && records.length === 0 ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          No analyses yet.
        </p>
      ) : null}

      <ul className="flex flex-col gap-3">
        {records.map((r) => {
          const topPathogenicity = Object.entries(r.summary.by_pathogenicity).sort(
            ([, a], [, b]) => b - a,
          )[0];
          return (
            <li
              key={r.id}
              className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="font-mono text-sm font-medium">{r.gene}</div>
                <time className="text-xs text-zinc-500 dark:text-zinc-400">
                  {new Date(r.created_at).toLocaleString()}
                </time>
              </div>
              <div className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">
                {r.query_length} bp · {r.variant_count} variant
                {r.variant_count === 1 ? "" : "s"}
                {topPathogenicity
                  ? ` · top ClinVar bucket: ${
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
