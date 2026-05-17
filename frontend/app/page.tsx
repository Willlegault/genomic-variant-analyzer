"use client";

import Link from "next/link";
import { useState } from "react";
import { Results } from "./components/Results";
import { SequenceForm } from "./components/SequenceForm";
import type { AnalysisResponse } from "./lib/types";

export default function Home() {
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-4 py-10 sm:px-8">
      <header className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between">
          <h1 className="text-5xl font-extrabold tracking-tight">
            Genomic Variant Analyzer
          </h1>
          <Link
            href="/history"
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            History →
          </Link>
        </div>
        <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          Analyze a short coding DNA sequence against a curated reference region.
          The app aligns your sequence, reports variant calls in HGVS-like
          notation, classifies coding consequences (synonymous / missense /
          nonsense / frameshift / in‑frame indel), looks up ClinVar records,
          and provides a plain‑language explanation for each variant.
        </p>
        <p className="max-w-2xl text-sm text-zinc-500 dark:text-zinc-400">
          Quick steps: 1) choose a reference, 2) paste an A/T/C/G sequence, 3)
          click "Analyze sequence". Use the built‑in BRCA1 example to see a
          typical frameshift result.
        </p>
      </header>

      <section className="rounded-lg border border-zinc-200 bg-white text-black p-5">
        <SequenceForm onResult={setResult} />
      </section>

      {result ? <Results result={result} /> : null}
    </main>
  );
}
