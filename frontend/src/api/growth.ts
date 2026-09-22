import api from './axios';

export const growthRoot = '/platform/growth';
export interface GrowthOffer { id: number; name: string; business_vertical: string; billing_model: string; currency: string; unit_amount: number; description: string }
export interface GrowthInvoice { id: number; tenant_id: number; contract_id: number; invoice_number: string; status: string; total_amount: number; currency: string; due_on: string }
export interface GrowthContract { id: number; tenant_id: number; offer_id: number; status: string; billing_interval: string | null; starts_on: string; next_billing_on: string | null }
export interface GrowthLead { id: number; name: string; email: string; company: string; business_vertical: string; stage: string; score: number; version: number; owner_id: number | null; contract_id: number | null; next_follow_up: string | null; signals: Record<string, boolean> }
export interface GrowthExperiment { id: number; name: string; status: string; kind: string; offer_id: number; minimum_sample: number }
export interface GrowthAnalytics { currency: string; scope: string; net_revenue: number; marketing_spend: number; new_paying_customers: number; cac: number | null; realized_ltv: number | null; forecast: { monthly_run_rate: number; weighted_open_pipeline: number; method: string }; risks: { tenant_id: number; contract_id: number; score: number; reasons: string[] }[]; risk_method: string; cohorts: { month: string; customers: number; repeat_paid_last_30d: number }[] }
export interface GrowthSnapshot {
  contracts: GrowthContract[]; invoices: GrowthInvoice[]; leads: GrowthLead[]; experiments: GrowthExperiment[];
  deliveries: { id: number; invoice_id: number; resource_type: string; status: string; tenant_id: number }[];
  tasks: { id: number; title: string; status: string; due_on: string }[];
  partner_balances: { partner_id: number; currency: string; available: number; unsettled: number }[];
  recommendations: { id: number; tenant_id: number; status: string; payload: { recommendations: { offer_id: number; kind: string; reason: string; discount_bps: number }[] } }[];
  validations: { id: number; area: string; environment: string; status: string; evidence: string; release_ref: string; recorded_at: string }[];
  analytics: GrowthAnalytics;
}
export const growthAPI = {
  snapshot: async () => (await api.get<GrowthSnapshot>(`${growthRoot}/admin`)).data,
  offers: async () => (await api.get<GrowthOffer[]>(`${growthRoot}/offers`)).data,
  post: async (path: string, data: unknown = {}) => (await api.post(`${growthRoot}${path}`, data)).data,
  put: async (path: string, data: unknown) => (await api.put(`${growthRoot}${path}`, data)).data,
  get: async <T,>(path: string) => (await api.get<T>(`${growthRoot}${path}`)).data,
  invoice: async (id: number) => {
    const response = await api.get(`${growthRoot}/invoices/${id}/document`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data); const link = document.createElement('a');
    link.href = url; link.download = `SashaInfinity-invoice-${id}.pdf`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
