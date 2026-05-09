import type {
  AnalysisRecord,
  AnalysisResponse,
  ReferenceMeta,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5001";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // ignore — non-JSON error bodies bubble up via status check below
  }

  if (!res.ok) {
    const message =
      (body as { error?: string } | null)?.error ?? `Request failed with ${res.status}`;
    throw new ApiError(message, res.status);
  }

  return body as T;
}

export function listReferences(): Promise<{ references: ReferenceMeta[] }> {
  return request("/api/references");
}

export function analyze(
  sequence: string,
  options: { reference_id?: string; skip_clinvar?: boolean } = {},
): Promise<AnalysisResponse> {
  return request("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ sequence, ...options }),
  });
}

export function getHistory(): Promise<{
  enabled: boolean;
  analyses: AnalysisRecord[];
}> {
  return request("/api/history");
}
