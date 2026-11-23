import type { CaseSummary, CaseView, ClinicProfile, FormSchema } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, `Can't reach the API at ${API_URL}. Is the backend running?`);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : res.statusText;
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  health: () =>
    request<{ ok: boolean; model: string; credential: string | null }>("/api/health"),
  schema: () => request<FormSchema>("/api/form-schema"),
  clinic: () => request<ClinicProfile>("/api/clinic"),
  saveClinic: (p: ClinicProfile) => request<ClinicProfile>("/api/clinic", { method: "PUT", body: json(p) }),
  cases: () => request<CaseSummary[]>("/api/cases"),
  createCase: (label: string) => request<CaseView>("/api/cases", { method: "POST", body: json({ label }) }),
  deleteCase: (id: string) => request<{ ok: boolean }>(`/api/cases/${id}`, { method: "DELETE" }),
  getCase: (id: string) => request<CaseView>(`/api/cases/${id}`),
  upload: (id: string, files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return request<CaseView>(`/api/cases/${id}/documents`, { method: "POST", body: fd });
  },
  deleteDocument: (id: string, docId: string) =>
    request<CaseView>(`/api/cases/${id}/documents/${docId}`, { method: "DELETE" }),
  retryDocument: (id: string, docId: string) =>
    request<CaseView>(`/api/cases/${id}/documents/${docId}/retry`, { method: "POST" }),
  setInclude: (id: string, docId: string, include_override: boolean | null) =>
    request<CaseView>(`/api/cases/${id}/documents/${docId}`, { method: "PATCH", body: json({ include_override }) }),
  setPrimaryPatient: (id: string, key: string | null) =>
    request<CaseView>(`/api/cases/${id}/primary-patient`, { method: "PUT", body: json({ key }) }),
  patchFields: (id: string, updates: Record<string, string>, reset: string[] = []) =>
    request<CaseView>(`/api/cases/${id}/fields`, { method: "PATCH", body: json({ updates, reset }) }),
  putTable: (id: string, table: "medications" | "assessments", rows: Record<string, string>[]) =>
    request<CaseView>(`/api/cases/${id}/tables/${table}`, { method: "PUT", body: json({ rows }) }),
  resetTable: (id: string, table: "medications" | "assessments") =>
    request<CaseView>(`/api/cases/${id}/tables/${table}`, { method: "DELETE" }),
  setSignature: (id: string, typed: boolean) =>
    request<CaseView>(`/api/cases/${id}/signature`, { method: "POST", body: json({ typed }) }),
  redraft: (id: string) => request<CaseView>(`/api/cases/${id}/narrative`, { method: "POST" }),
  pdfUrl: (id: string) => `${API_URL}/api/cases/${id}/pdf`,
  fileUrl: (id: string, docId: string) => `${API_URL}/api/cases/${id}/documents/${docId}/file`,
  previewUrl: (id: string, docId: string, page: number, quote?: string) =>
    `${API_URL}/api/cases/${id}/documents/${docId}/preview?page=${page}${quote ? `&quote=${encodeURIComponent(quote)}` : ""}`,
};
