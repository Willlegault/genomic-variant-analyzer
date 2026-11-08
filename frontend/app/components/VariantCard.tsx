import type { Variant } from "../lib/types";
import {
  EFFECT_COLORS,
  EFFECT_LABELS,
  PATHOGENICITY_COLORS,
  PATHOGENICITY_LABELS,
  tint,
} from "../lib/style";

export function VariantCard({ variant }: { variant: Variant }) {
  const pathogenicityColor = PATHOGENICITY_COLORS[variant.pathogenicity];
  const pathogenicityLabel = PATHOGENICITY_LABELS[variant.pathogenicity];

  return (
    <article className="glass flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
            HGVS
          </div>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <code className="font-mono text-lg font-semibold text-fg">{variant.hgvs_c}</code>
            {variant.hgvs_p ? (
              <code className="font-mono text-sm text-accent-2">{variant.hgvs_p}</code>
            ) : null}
          </div>
        </div>
        <span
          className="rounded-full border px-2.5 py-0.5 text-xs font-semibold"
          style={tint(pathogenicityColor)}
        >
          {pathogenicityLabel}
        </span>
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <span
          className="rounded-full border px-2.5 py-0.5 font-medium"
          style={tint(EFFECT_COLORS[variant.effect])}
        >
          {EFFECT_LABELS[variant.effect]}
        </span>
        <Pill>pos {variant.position}</Pill>
        {variant.ref_codon && variant.alt_codon ? (
          <Pill>
            codon {variant.codon_number} {variant.ref_codon} → {variant.alt_codon}
          </Pill>
        ) : null}
        {variant.ref_aa && variant.alt_aa ? (
          <Pill>
            aa {variant.ref_aa} → {variant.alt_aa === "*" ? "Stop" : variant.alt_aa}
          </Pill>
        ) : null}
        {variant.notes.map((n) => (
          <Pill key={n}>{n}</Pill>
        ))}
      </div>

      <details className="group text-sm">
        <summary className="flex cursor-pointer select-none list-none items-center gap-2 font-semibold text-fg [&::-webkit-details-marker]:hidden">
          <span className="inline-block text-accent transition group-open:rotate-90">›</span>
          {variant.explanation.headline}
        </summary>
        <div className="mt-2 flex flex-col gap-2 pl-4">
          <p className="leading-relaxed text-muted">{variant.explanation.body}</p>
          {variant.explanation.context.map((c, i) => (
            <p
              key={i}
              className="rounded-lg border border-accent-2/30 bg-accent-2/10 px-3 py-2 text-[13px] leading-relaxed text-fg"
            >
              {c}
            </p>
          ))}
        </div>
      </details>

      <ClinVarSection variant={variant} />
    </article>
  );
}

function ClinVarSection({ variant }: { variant: Variant }) {
  const cv = variant.clinvar;
  const base = "border-t border-line pt-3 text-xs";

  if (cv?.skipped) {
    return <p className={`${base} text-muted`}>ClinVar skipped</p>;
  }

  if (cv?.error) {
    return <p className={`${base} text-red-300`}>ClinVar error: {cv.error}</p>;
  }

  if (!cv?.found) {
    return (
      <p className={`${base} text-muted`} title={`Searched: ${cv?.query ?? ""}`}>
        Not in ClinVar
      </p>
    );
  }

  const url = cv.clinvar_id
    ? `https://www.ncbi.nlm.nih.gov/clinvar/variation/${cv.clinvar_id}/`
    : null;

  return (
    <div className={`${base} flex flex-wrap items-baseline justify-between gap-2 text-muted`}>
      <div className="flex flex-col gap-0.5">
        <div>
          ClinVar: <span className="font-semibold text-fg">{cv.classification ?? "—"}</span>
        </div>
        {cv.title ? <div className="font-mono">{cv.title}</div> : null}
      </div>
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-accent hover:underline"
        >
          Record {cv.clinvar_id} ↗
        </a>
      ) : null}
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-line bg-white/5 px-2.5 py-0.5 text-muted">
      {children}
    </span>
  );
}
