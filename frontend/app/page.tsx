"use client";

import Link from "next/link";
import { useState } from "react";
import { Results } from "./components/Results";
import { SequenceForm } from "./components/SequenceForm";
import type { AnalysisResponse } from "./lib/types";

const STEPS = ["Pick a reference", "Paste a sequence or load the demo", "Analyze"];

export default function Home() {
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-10 sm:px-8">
      <header className="glass flex flex-col gap-5 p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
            Biopython · ClinVar · HGVS
          </span>
          <Link
            href="/history"
            className="rounded-full border border-line px-3 py-1 text-sm text-fg transition hover:border-accent hover:text-accent"
          >
            History →
          </Link>
        </div>
        <div className="flex flex-col gap-3">
          <h1 className="text-4xl font-bold tracking-tight text-balance sm:text-5xl">
            Genomic Variant Analyzer
          </h1>
          <p className="max-w-2xl text-[15px] leading-relaxed text-muted">
            Find DNA variants against a reference gene, see what each does to the
            protein, and check it in ClinVar.
          </p>
        </div>
        <ol className="grid gap-3 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step} className="flex items-start gap-3 text-sm text-muted">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/15 font-mono text-xs font-semibold text-accent">
                {i + 1}
              </span>
              <span className="pt-0.5">{step}</span>
            </li>
          ))}
        </ol>
      </header>

      <section className="glass p-6 sm:p-8">
        <SequenceForm onResult={setResult} />
      </section>

      {result ? <Results result={result} /> : null}
    </main>
  );
}
