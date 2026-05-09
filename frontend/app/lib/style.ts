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
};

export const PATHOGENICITY_COLORS: Record<Pathogenicity, string> = {
  pathogenic: "#dc2626",
  likely_pathogenic: "#ea580c",
  uncertain: "#ca8a04",
  conflicting: "#7c3aed",
  likely_benign: "#0891b2",
  benign: "#16a34a",
  other: "#64748b",
  unknown: "#94a3b8",
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
  synonymous: "#16a34a",
  missense: "#ca8a04",
  nonsense: "#dc2626",
  frameshift: "#dc2626",
  in_frame_insertion: "#0891b2",
  in_frame_deletion: "#0891b2",
  unknown: "#94a3b8",
};
