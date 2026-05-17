import type { Variant } from "../lib/types";
import {
  EFFECT_LABELS,
  PATHOGENICITY_COLORS,
  PATHOGENICITY_LABELS,
} from "../lib/style";

export function VariantCard({ variant }: { variant: Variant }) {
  const pathogenicityColor = PATHOGENICITY_COLORS[variant.pathogenicity];
  const pathogenicityLabel = PATHOGENICITY_LABELS[variant.pathogenicity];
  const effectLabel = EFFECT_LABELS[variant.effect];

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div className="flex flex-col">
            <div className="text-xs text-zinc-500 dark:text-zinc-400">HGVS (coding)</div>
            <div className="flex items-baseline gap-3">
              <code className="font-mono text-sm font-semibold">{variant.hgvs_c}</code>
              {variant.hgvs_p ? (
                <code className="font-mono text-xs text-zinc-500 dark:text-zinc-400">
                  {variant.hgvs_p}
                </code>
              ) : null}
            </div>
          </div>
        <span
          className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
          style={{ backgroundColor: pathogenicityColor }}
        >
          {pathogenicityLabel}
        </span>
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <Pill>{effectLabel}</Pill>
        <Pill>position {variant.position}</Pill>
        {variant.ref_codon && variant.alt_codon ? (
          <Pill>
            codon {variant.codon_number}: {variant.ref_codon} → {variant.alt_codon}
          </Pill>
        ) : null}
        {variant.ref_aa && variant.alt_aa ? (
          <Pill>
            aa: {variant.ref_aa} → {variant.alt_aa === "*" ? "Stop" : variant.alt_aa}
          </Pill>
        ) : null}
      </div>

      <div className="flex flex-col gap-2 text-sm">
        <p className="font-medium">{variant.explanation.headline}</p>
        <p className="text-zinc-700 dark:text-zinc-300">
          {variant.explanation.body}
        </p>
        {variant.explanation.context.map((c, i) => (
          <p
            key={i}
            className="rounded-md border-l-2 border-blue-400 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:bg-blue-950 dark:text-blue-200"
          >
            {c}
          </p>
        ))}
      </div>

      <ClinVarSection variant={variant} />
    </div>
  );
}

function ClinVarSection({ variant }: { variant: Variant }) {
  const cv = variant.clinvar;

  if (cv?.skipped) {
    return (
      <p className="text-xs text-zinc-500 dark:text-zinc-400">
        ClinVar lookup skipped — pathogenicity was not queried for this run.
      </p>
    );
  }

  if (cv?.error) {
    return (
      <p className="text-xs text-red-600 dark:text-red-400">
        ClinVar lookup error: {cv.error}
      </p>
    );
  }

  if (!cv?.found) {
    return (
      <p className="text-xs text-zinc-500 dark:text-zinc-400">
        No ClinVar record found for this variant (query: <code className="font-mono">{cv?.query}</code>).
      </p>
    );
  }

  const url = cv.clinvar_id
    ? `https://www.ncbi.nlm.nih.gov/clinvar/variation/${cv.clinvar_id}/`
    : null;

  return (
    <div className="flex flex-col gap-1 text-xs text-zinc-600 dark:text-zinc-400">
      <div>
        ClinVar:{" "}
        <span className="font-medium text-zinc-800 dark:text-zinc-200">
          {cv.classification ?? "—"}
        </span>
      </div>
      {cv.title ? <div className="text-zinc-500">{cv.title}</div> : null}
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline dark:text-blue-400"
        >
          View on ClinVar →
        </a>
      ) : null}
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
      {children}
    </span>
  );
}
