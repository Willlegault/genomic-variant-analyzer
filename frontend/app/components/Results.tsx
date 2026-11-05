import type { AnalysisResponse } from "../lib/types";
import { EffectChart, PathogenicityChart } from "./Charts";
import { VariantCard } from "./VariantCard";

export function Results({ result }: { result: AnalysisResponse }) {
  const { variants, summary, reference, query } = result;

  if (variants.length === 0) {
    return (
      <div className="glass border-emerald-400/40 p-6">
        <h2 className="text-lg font-semibold text-emerald-300">No variants</h2>
        <p className="mt-2 text-sm text-muted">
          All {query.length} bp match the {reference.gene} reference.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="glass flex flex-wrap items-baseline justify-between gap-2 p-5">
        <h2 className="text-xl font-semibold">
          {summary.total} variant{summary.total === 1 ? "" : "s"} in{" "}
          <span className="font-mono text-accent">{reference.gene}</span>
        </h2>
        <p className="text-sm text-muted">{reference.pathway}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ChartCard title="ClinVar classification">
          <PathogenicityChart counts={summary.by_pathogenicity} />
        </ChartCard>
        <ChartCard title="Effect on protein">
          <EffectChart counts={summary.by_effect} />
        </ChartCard>
      </div>

      <div className="flex flex-col gap-3">
        <h3 className="px-1 font-mono text-xs uppercase tracking-[0.16em] text-muted">
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
    <div className="glass flex flex-col gap-1 p-5">
      <h3 className="font-mono text-xs uppercase tracking-[0.16em] text-fg">{title}</h3>
      {children}
    </div>
  );
}
