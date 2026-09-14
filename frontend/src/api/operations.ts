import { api } from "./axios";
export interface QueueItem {
  id: number;
  title: string;
  href: string;
  age_hours: number | null;
}
export interface OperationsSummary {
  queues: { key: string; label: string; count: number; items: QueueItem[] }[];
  outcomes: {
    courses: {
      course_id: number;
      title: string;
      learners: number;
      completed: number;
      completion_rate: number;
      mean_progress: number;
    }[];
    struggling_concepts: { concept: string; open_interventions: number }[];
    paired_interventions: number;
    mean_delayed_change: number | null;
  };
  health: {
    database: string;
    transcription: { configured: boolean; note: string };
    services: {
      name: string;
      status: string;
      last_seen: string | null;
      age_seconds: number | null;
    }[];
    storage: { status?: "ok" | "unavailable"; free_bytes: number | null; total_bytes: number | null; free_percent: number | null };
    recording_jobs: Record<string, number>;
    note: string;
  };
  as_of: string;
}
export interface RevenueReport {
  from: string;
  to: string;
  currencies: {
    currency: string;
    captured: number;
    refunded: number;
    net_cash: number;
  }[];
  estimated_active_mrr_inr: number;
  failed_payments: number;
  refunds_needing_attention: number;
  refunds_missing_timestamp: number;
  note: string;
}
export interface PortfolioCurrency {
  currency: string;
  captured: number;
  refunded: number;
  net_cash: number;
}
export interface PortfolioRevenueStream {
  key: string;
  label: string;
  currencies: PortfolioCurrency[];
}
export interface BusinessPortfolioReport {
  from: string;
  to: string;
  as_of: string;
  verticals: {
    key: "meiporul" | "seyappaduporul" | "utporul";
    code: string;
    label: string;
    tamil: string;
    subdomain: string;
    mission: string;
    business_model: string;
    inventory: { key: string; label: string; value: number }[];
    revenue: {
      currencies: PortfolioCurrency[];
      streams: PortfolioRevenueStream[];
    };
  }[];
  unallocated: {
    currencies: PortfolioCurrency[];
    payment_count: number;
    course_count: number;
  };
  resilience: {
    currency: string;
    leader: "meiporul" | "seyappaduporul" | "utporul" | null;
    largest_share_percent: number | null;
    remaining_if_leader_pauses: number;
    status: "concentrated" | "balanced_mix" | "no_revenue";
  }[];
  reporting_contract: {
    operating_sources: string[];
    rule: string;
  };
}
export interface AdminRow {
  id: number | string;
  name: string;
  detail: string;
  status: string;
  created: string | null;
  amount: number | null;
  href: string;
}
export interface AdminRows {
  items: AdminRow[];
  total: number;
  page: number;
  page_size: number;
}
export const operationsAPI = {
  summary: async () =>
    (await api.get<OperationsSummary>("/admin/operations/summary")).data,
  revenue: async (start: string, end: string) =>
    (
      await api.get<RevenueReport>("/admin/operations/revenue", {
        params: { start, end },
      })
    ).data,
  portfolio: async (start: string, end: string) =>
    (
      await api.get<BusinessPortfolioReport>("/admin/operations/portfolio", {
        params: { start, end },
      })
    ).data,
  rows: async (dataset: string, params: Record<string, string | number>) =>
    (await api.get<AdminRows>(`/admin/operations/lists/${dataset}`, { params }))
      .data,
  csv: async (dataset: string, params: Record<string, string | number>) =>
    (
      await api.get<Blob>(`/admin/operations/lists/${dataset}/export.csv`, {
        params,
        responseType: "blob",
      })
    ).data,
};
export function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
