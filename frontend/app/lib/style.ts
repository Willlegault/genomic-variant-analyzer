import type { Pathogenicity, VariantEffect } from "./types";

export const PATHOGENICITY_LABELS: Record<Pathogenicity, string> = {
  pathogenic: "Pathogenic",
  likely_pathogenic: "Likely pathogenic",
  benign: "Benign",
  likely_benign: "Likely benign",
  uncertain: "Uncertain significance",
  conflicting: "Conflicting",
  other: "Other",
  unknown: "Not in ClinVar",
  not_checked: "Not checked",
};

// Light tones: these are drawn on dark navy panels (text, outlines, chart fills).
export const PATHOGENICITY_COLORS: Record<Pathogenicity, string> = {
  pathogenic: "#f87171",
  likely_pathogenic: "#fb923c",
  uncertain: "#facc15",
  conflicting: "#c4b5fd",
  likely_benign: "#22d3ee",
  benign: "#4ade80",
  other: "#94a3b8",
  unknown: "#94a3b8",
  not_checked: "#64748b",
};

export const EFFECT_LABELS: Record<VariantEffect, string> = {
  synonymous: "Synonymous",
  missense: "Missense",
  nonsense: "Nonsense",
  frameshift: "Frameshift",
  in_frame_insertion: "In-frame insertion",
  in_frame_deletion: "In-frame deletion",
  unknown: "Unclassified",
};

export const EFFECT_COLORS: Record<VariantEffect, string> = {
  synonymous: "#4ade80",
  missense: "#facc15",
  nonsense: "#f87171",
  frameshift: "#f87171",
  in_frame_insertion: "#22d3ee",
  in_frame_deletion: "#22d3ee",
  unknown: "#94a3b8",
};

// Recharts draws SVG attributes, which can't read CSS variables — mirror globals.css.
export const CHART_THEME = {
  text: "#b6c4dc",
  grid: "rgba(148, 197, 255, 0.12)",
  tooltipBg: "#0b1733",
  tooltipBorder: "rgba(148, 197, 255, 0.25)",
  tooltipText: "#eef4ff",
  cursor: "rgba(255, 255, 255, 0.05)",
};

/** Tinted badge style: coloured text on a faint wash of the same colour. */
export function tint(color: string) {
  return {
    color,
    backgroundColor: `${color}1f`,
    borderColor: `${color}66`,
  };
}
