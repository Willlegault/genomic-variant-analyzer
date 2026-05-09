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
          <h1 className="text-2xl font-semibold tracking-tight">
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
          Detect and classify DNA sequence variants against a reference CDS,
          look up pathogenicity in ClinVar, and explain the coding consequence
          (synonymous, missense, nonsense, frameshift, in-frame indel).
        </p>
      </header>

      <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
        <SequenceForm onResult={setResult} />
      </section>

      {result ? <Results result={result} /> : null}
    </main>
  );
}
