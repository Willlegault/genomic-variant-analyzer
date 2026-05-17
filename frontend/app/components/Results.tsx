import type { AnalysisResponse } from "../lib/types";
import { EffectChart, PathogenicityChart } from "./Charts";
import { VariantCard } from "./VariantCard";

export function Results({ result }: { result: AnalysisResponse }) {
  const { variants, summary, reference, query } = result;

  if (variants.length === 0) {
    return (
      <div className="rounded-lg border border-green-300 bg-green-50 p-6 dark:border-green-900 dark:bg-green-950">
        <h2 className="text-lg font-semibold text-green-900 dark:text-green-100">
          No variants detected.
        </h2>
        <p className="mt-2 text-sm text-green-800 dark:text-green-200">
          The {query.length} bp query matches the {reference.gene} reference exactly.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-base font-semibold">
          {summary.total} variant{summary.total === 1 ? "" : "s"} detected in{" "}
          {reference.gene}
        </h2>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
          Pathway: {reference.pathway}.
        </p>
      </div>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-600 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-400">
        Charts: <strong>Pathogenicity</strong> shows ClinVar buckets for matched
        variants (if looked up). <strong>Coding consequence</strong> summarizes
        the predicted molecular effect (synonymous / missense / nonsense /
        frameshift / in-frame indel).
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ChartCard title="Pathogenicity (ClinVar)">
          <PathogenicityChart counts={summary.by_pathogenicity} />
        </ChartCard>
        <ChartCard title="Coding consequence">
          <EffectChart counts={summary.by_effect} />
        </ChartCard>
      </div>

      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Variants
        </h3>
        {variants.map((v, i) => (
          <VariantCard key={`${v.hgvs_c}-${i}`} variant={v} />
        ))}
      </div>
    </div>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {title}
      </h3>
      {children}
    </div>
  );
}
