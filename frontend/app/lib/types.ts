export type VariantType = "snp" | "insertion" | "deletion";

export type VariantEffect =
  | "synonymous"
  | "missense"
  | "nonsense"
  | "frameshift"
  | "in_frame_insertion"
  | "in_frame_deletion"
  | "unknown";

export type Pathogenicity =
  | "pathogenic"
  | "likely_pathogenic"
  | "benign"
  | "likely_benign"
  | "uncertain"
  | "conflicting"
  | "other"
  | "unknown";

export interface ClinVarResult {
  found?: boolean;
  classification?: string | null;
  clinvar_id?: string | null;
  title?: string | null;
  query?: string;
  error?: string | null;
  skipped?: boolean;
}

export interface Explanation {
  headline: string;
  body: string;
  context: string[];
  gene: string;
  pathway: string;
}

export interface Variant {
  type: VariantType;
  effect: VariantEffect;
  position: number;
  ref_allele: string;
  alt_allele: string;
  hgvs_c: string;
  hgvs_p: string | null;
  codon_number: number | null;
  ref_codon: string | null;
  alt_codon: string | null;
  ref_aa: string | null;
  alt_aa: string | null;
  notes: string[];
  clinvar: ClinVarResult;
  pathogenicity: Pathogenicity;
  explanation: Explanation;
}

export interface ReferenceMeta {
  id: string;
  gene: string;
  description: string;
  pathway: string;
  clinical_context: string;
  source: string;
  length: number;
}

export interface AnalysisSummary {
  total: number;
  by_type: Record<string, number>;
  by_effect: Record<string, number>;
  by_pathogenicity: Record<string, number>;
}

export interface AnalysisResponse {
  reference: ReferenceMeta;
  query: { length: number; sequence: string };
  variants: Variant[];
  summary: AnalysisSummary;
  analysis_id?: string;
}

export interface AnalysisRecord {
  id: string;
  created_at: string;
  reference_id: string;
  gene: string;
  query_sequence: string;
  query_length: number;
  variant_count: number;
  summary: AnalysisSummary;
  variants: Variant[];
}
