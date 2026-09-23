/* eslint-disable @typescript-eslint/no-explicit-any */
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000") + "/api";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch {
    throw new ApiError(
      `Network error: Unable to reach the backend at ${url}. Is the server running?`,
      0
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body.detail || `API error: ${response.status} ${response.statusText}`,
      response.status
    );
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface DashboardData {
  total_cases: number;
  fraud_cases: number;
  cleared_cases: number;
  uncertain_cases: number;
  high_risk_cases: number;
  active_investigations: number;
  cases_awaiting_approval: number;
  avg_fraud_probability: number;
  top_patterns: { pattern: string; count: number }[];
}

export async function getDashboard(): Promise<DashboardData> {
  return fetchApi<DashboardData>("/dashboard");
}

// ---------------------------------------------------------------------------
// Cases (completed, on-disk)
// ---------------------------------------------------------------------------

export interface CaseSummary {
  case_id: string;
  status: string;
  final_verdict: string | null;
  final_risk_level: string | null;
  fraud_probability: number | null;
  final_fraud_probability?: number | null;
  pattern: string | null;
  trigger_type?: string | null;
  created_at: string | null;
  txn_id: string | null;
}

export interface CasesListResponse {
  cases: CaseSummary[];
  total: number;
  limit: number;
  offset: number;
}

export async function getCases(verdict?: string): Promise<CasesListResponse> {
  const params = verdict ? `?verdict=${verdict}` : "";
  return fetchApi<CasesListResponse>(`/cases${params}`);
}

export async function getCase(caseId: string): Promise<any> {
  return fetchApi<any>(`/cases/${caseId}`);
}

// ---------------------------------------------------------------------------
// Investigations (live, in-memory)
// ---------------------------------------------------------------------------

export interface InvestigationSummary {
  case_id: string;
  status: string;
  started_at: string;
  error?: string | null;
}

export interface InvestigationListResponse {
  investigations: InvestigationSummary[];
  total: number;
}

export async function getInvestigations(): Promise<InvestigationListResponse> {
  return fetchApi<InvestigationListResponse>("/investigations");
}

export async function getInvestigation(caseId: string): Promise<any> {
  return fetchApi<any>(`/investigations/${caseId}`);
}

export async function createInvestigation(data: {
  txn_id: string;
  trigger_type?: string;
  card_id?: string;
  customer_id?: string;
  trigger_risk_score?: number;
  case_id?: string;
}): Promise<{ case_id: string; status: string; message: string }> {
  return fetchApi("/investigations", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Case Details & Actions
// ---------------------------------------------------------------------------

export async function getTimeline(caseId: string): Promise<{ timeline: any[]; total: number }> {
  return fetchApi(`/investigations/${caseId}/timeline`);
}

export async function getEvidence(caseId: string): Promise<{ evidence: any[]; total: number }> {
  return fetchApi(`/investigations/${caseId}/evidence`);
}

export async function getGraph(caseId: string): Promise<any> {
  return fetchApi(`/investigations/${caseId}/graph`);
}

export async function getRecommendation(caseId: string): Promise<any> {
  return fetchApi(`/investigations/${caseId}/recommendation`);
}

export async function approveAction(caseId: string, action: string, notes?: string): Promise<any> {
  return fetchApi(`/investigations/${caseId}/approve`, {
    method: "POST",
    body: JSON.stringify({ action, approved_by: "Analyst", notes }),
  });
}

export async function rejectAction(caseId: string, action: string, notes?: string): Promise<any> {
  return fetchApi(`/investigations/${caseId}/reject`, {
    method: "POST",
    body: JSON.stringify({ action, approved_by: "Analyst", notes }),
  });
}

// ---------------------------------------------------------------------------
// Policies
// ---------------------------------------------------------------------------

export interface PolicyRule {
  rule_id: string;
  description: string;
  threshold: string | null;
  actions: string[];
  approval_route: string;
}

export interface PolicyResponse {
  rules: PolicyRule[];
  actions: { action: string; route: string; description: string }[];
  total_rules: number;
}

export async function getPolicies(): Promise<PolicyResponse> {
  return fetchApi<PolicyResponse>("/policies");
}

// ---------------------------------------------------------------------------
// Memory (historical closed cases)
// ---------------------------------------------------------------------------

export interface MemoryCase {
  case_id: string;
  customer_id: string | null;
  card_id: string | null;
  outcome: string;
  pattern: string;
  exposure_usd: number;
  actions_taken: string[];
  report_filed: boolean;
  analyst_notes: string | null;
  opened_at: string | null;
  closed_at: string | null;
}

export interface MemoryResponse {
  historical_cases: MemoryCase[];
  total: number;
}

export async function getMemory(pattern?: string, outcome?: string): Promise<MemoryResponse> {
  const params = new URLSearchParams();
  if (pattern) params.set("pattern", pattern);
  if (outcome) params.set("outcome", outcome);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return fetchApi<MemoryResponse>(`/memory${qs}`);
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<{
  status: string;
  service: string;
  version: string;
  timestamp: string;
  tg_connected: boolean;
}> {
  return fetchApi("/health");
}
