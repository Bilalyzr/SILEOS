import { api } from "./axios";

export type VerticalKey = "meiporul" | "seyappaduporul" | "utporul";
export type TenantStatus = "trial" | "active" | "suspended" | "archived";

export interface PlatformTenantSummary {
  id: number;
  slug: string;
  name: string;
  kind: "platform" | "institution" | "franchise" | "company" | "creator";
  status: TenantStatus;
  timezone: string;
  data_region: string;
  counts: { members: number; domains: number; entitlements: number };
}

export interface PlatformTenantDetail extends Omit<PlatformTenantSummary, "counts"> {
  members: { id: number; user_id: number; role: string; status: string; permissions: string[] }[];
  domains: { id: number; hostname: string; vertical: VerticalKey | null; status: string; is_primary: boolean; verified_at: string | null }[];
  entitlements: { id: number; vertical: VerticalKey; feature_key: string; enabled: boolean; quota: Record<string, unknown>; effective_from: string | null; effective_through: string | null }[];
}

export interface CommercialOffer {
  id: number;
  sku: string;
  business_vertical: VerticalKey;
  revenue_stream: string;
  name: string;
  description: string;
  billing_model: "one_time" | "subscription" | "usage" | "royalty" | "milestone";
  currency: string;
  unit_amount: number;
  tax_code: string;
  entitlement_grants: { vertical: VerticalKey; feature_key: string; quota: Record<string, unknown> }[];
  is_active: boolean;
}

export interface CommercialContract {
  id: number;
  tenant_id: number;
  offer_id: number;
  status: string;
  quantity: number;
  unit_amount: number;
  currency: string;
  billing_interval: string | null;
  starts_on: string;
}

export interface CommercialInvoice {
  id: number;
  tenant_id: number;
  contract_id: number;
  invoice_number: string;
  status: string;
  currency: string;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total_amount: number;
  due_on: string;
}

export interface RevenueLedgerEvent {
  id: number;
  tenant_id: number | null;
  business_vertical: VerticalKey;
  revenue_stream: string;
  event_type: "capture" | "refund" | "adjustment";
  currency: string;
  gross_amount: number;
  net_amount: number;
  occurred_at: string;
  source_event_key: string;
}

export const platformAPI = {
  tenants: async () =>
    (await api.get<PlatformTenantSummary[]>("/platform/tenants")).data,
  tenant: async (tenantId: number) =>
    (await api.get<PlatformTenantDetail>(`/platform/tenants/${tenantId}`)).data,
  setTenantStatus: async (tenantId: number, status: TenantStatus, reason: string) =>
    (await api.patch(`/platform/tenants/${tenantId}/status`, { status, reason })).data,
  setEntitlement: async (
    tenantId: number,
    vertical: VerticalKey,
    featureKey: string,
    enabled: boolean,
    quota: Record<string, unknown>,
    reason: string,
  ) =>
    (
      await api.put(
        `/platform/tenants/${tenantId}/entitlements/${vertical}/${featureKey}`,
        { enabled, quota, reason },
      )
    ).data,
  addDomain: async (tenantId: number, hostname: string, vertical: VerticalKey | null) =>
    (
      await api.post(`/platform/tenants/${tenantId}/domains`, {
        hostname,
        vertical,
        is_primary: false,
      })
    ).data,
  offers: async () =>
    (await api.get<CommercialOffer[]>("/platform/commercial/offers")).data,
  createOffer: async (payload: Record<string, unknown>) =>
    (await api.post<CommercialOffer>("/platform/commercial/offers", payload)).data,
  createContract: async (payload: Record<string, unknown>) =>
    (await api.post<CommercialContract>("/platform/commercial/contracts", payload)).data,
  createInvoice: async (payload: Record<string, unknown>) =>
    (await api.post<CommercialInvoice>("/platform/commercial/invoices", payload)).data,
  recordPayment: async (invoiceId: number, payload: Record<string, unknown>) =>
    (
      await api.post<RevenueLedgerEvent>(
        `/platform/commercial/invoices/${invoiceId}/payments`,
        payload,
      )
    ).data,
  ledger: async (start: string, end: string) =>
    (
      await api.get<RevenueLedgerEvent[]>("/platform/commercial/ledger", {
        params: { start, end },
      })
    ).data,
};
