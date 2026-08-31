import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: BASE, timeout: 30000 });

// ── Types ──────────────────────────────────────────────────────────────────────
export interface Run {
  run_id: string; started_at: string; completed_at: string | null;
  total_records: number; matched: number; exceptions: number;
  match_rate: number; amount_reconciled: number; status: string;
}
export interface DashboardStats {
  total_records: number; matched: number; exceptions: number;
  match_rate: number; amount_reconciled: number;
  auto_resolved: number; pending_review: number;
  exception_breakdown: Record<string, number>;
  severity_breakdown: Record<string, number>;
}
export interface Exception {
  exception_id: string; order_id: string | null; exception_type: string;
  severity: "low" | "warning" | "critical"; amount_delta: number | null;
  status: "open" | "auto_resolved" | "manual_review" | "resolved";
  resolution: string | null; created_at: string; run_id: string;
  investigation?: Investigation;
}
export interface Investigation {
  root_cause: string; classification: string; confidence: number;
  explanation: string; recommended_action: string;
  evidence: string; tool_calls: string; risk_level: string; auto_resolved: boolean;
}
export interface AuditLog {
  entity_type: string; entity_id: string; action: string;
  actor: string; detail: string | null; created_at: string;
}

// ── API calls ──────────────────────────────────────────────────────────────────
export const runReconciliation  = ()                        => api.post<Run>("/api/reconciliation/run", {});
export const getRuns            = ()                        => api.get<Run[]>("/api/reconciliation/runs");
export const getDashboard       = ()                        => api.get<DashboardStats>("/api/reconciliation/dashboard");
export const getExceptions      = (runId?: string)          => api.get<Exception[]>("/api/exceptions", { params: { run_id: runId, limit: 200 } });
export const getException       = (id: string)              => api.get<Exception>(`/api/exceptions/${id}`);
export const investigateException = (id: string)            => api.post<Investigation>(`/api/exceptions/${id}/investigate`);
export const resolveException   = (id: string, res: string) => api.post(`/api/exceptions/${id}/resolve`, { resolution: res, actor: "user" });
export const flagException      = (id: string, reason?: string) => api.post(`/api/exceptions/${id}/flag`, { reason: reason ?? "Flagged for manual review", actor: "user" });
export const getAuditLogs       = (runId?: string)          => api.get<AuditLog[]>("/api/audit", { params: { run_id: runId, limit: 200 } });
export const getOrders          = ()                        => api.get("/api/transactions/orders?limit=200");
export const getSettlements     = ()                        => api.get("/api/transactions/settlements?limit=200");
export const getBankTxns        = ()                        => api.get("/api/transactions/bank?limit=200");
