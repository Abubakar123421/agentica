import type { CaseDetail, CaseSummary, Escalation, Inspection, User } from "./types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...options, headers, credentials: "include" });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/api/v1/auth/me"),
  login: (email: string, password: string) =>
    request<User>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  report: (payload: Record<string, string>) =>
    request<{ case_id: string; tracking_token: string; tracking_url: string; status: string }>(
      "/api/v1/reports",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  track: (token: string) =>
    request<{
      case_id: string;
      product_name: string;
      status: string;
      safety_verdict: string;
      updated_at: string;
    }>(`/api/v1/tracking/${encodeURIComponent(token)}`),
  cases: () => request<CaseSummary[]>("/api/v1/cases"),
  caseDetail: (caseId: string) => request<CaseDetail>(`/api/v1/cases/${caseId}`),
  startAgent: (caseId: string, agent: "triage" | "traceability" | "escalation") => {
    const suffix =
      agent === "triage"
        ? "triage"
        : agent === "traceability"
          ? "analysis"
          : "escalation-analysis";
    return request<{ run_id: string; status: string; agent_type: string }>(
      `/api/v1/cases/${caseId}/${suffix}`,
      { method: "POST" },
    );
  },
  reviewCase: (caseId: string, decision: string, notes: string) =>
    request(`/api/v1/cases/${caseId}/retailer-review`, {
      method: "POST",
      body: JSON.stringify({ decision, notes }),
    }),
  approve: (caseId: string, proposalId: string, decision: string, notes: string) =>
    request(`/api/v1/cases/${caseId}/approvals`, {
      method: "POST",
      body: JSON.stringify({ proposal_id: proposalId, decision, notes }),
    }),
  inspections: () => request<Inspection[]>("/api/v1/inspections"),
  submitFinding: (inspectionId: string, finding: string, notes: string) =>
    request(`/api/v1/inspections/${inspectionId}/finding`, {
      method: "POST",
      body: JSON.stringify({ finding, notes }),
    }),
  importCsv: (kind: "batches" | "shipments", file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{ inserted: number; skipped: number; errors: Record<string, unknown>[] }>(
      `/api/v1/imports/${kind}`,
      { method: "POST", body },
    );
  },
  escalations: () => request<Escalation[]>("/api/v1/escalations"),
  respond: (escalationId: string, response: string) =>
    request(`/api/v1/escalations/${escalationId}/response`, {
      method: "POST",
      body: JSON.stringify({ response }),
    }),
};
