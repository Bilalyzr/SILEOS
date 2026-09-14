import { api } from "@/api/axios";

export type CampusDomain = {
  id: number;
  hostname: string;
  status: "pending" | "verified" | "failed";
  is_primary: boolean;
  verification: { record_type: string; record_name: string; record_value: string };
  verified_at?: string;
};

export type CampusIntegration = {
  id: number;
  kind: string;
  display_name: string;
  status: "draft" | "ready" | "active" | "paused";
  config: Record<string, unknown>;
  has_secret_reference: boolean;
  last_sync_at?: string;
  last_error: string;
  updated_at?: string;
};

export type PrivacyRequest = {
  id: number;
  requester_user_id: number;
  subject_user_id: number;
  kind: string;
  status: string;
  detail: string;
  resolution_note: string;
  due_at: string;
  resolved_at?: string;
  created_at: string;
};

export type RetentionPolicy = {
  inactive_account_days: number;
  learning_record_days: number;
  financial_record_days: number;
  application_record_days: number;
  legal_hold: boolean;
};

export type ControlPlane = {
  domains: CampusDomain[];
  integrations: CampusIntegration[];
  retention: RetentionPolicy;
  privacy_requests: PrivacyRequest[];
  standards: { key: string; version: string; capability: string }[];
};

export type IntegrationKind =
  | "google_workspace"
  | "microsoft_entra"
  | "saml"
  | "oidc"
  | "scim"
  | "oneroster"
  | "lti_1_3"
  | "digilocker_nad";

export const campusControlPlaneApi = {
  get: async (institutionId: number) =>
    (await api.get<ControlPlane>(`/institutions/${institutionId}/control-plane`)).data,
  addDomain: async (institutionId: number, hostname: string) =>
    (await api.post<CampusDomain>(`/institutions/${institutionId}/control-plane/domains`, { hostname })).data,
  saveIntegration: async (
    institutionId: number,
    input: { kind: IntegrationKind; display_name: string; status: "draft" | "ready" | "active" | "paused"; config: Record<string, unknown>; secret_reference: string },
  ) =>
    (await api.put<CampusIntegration>(`/institutions/${institutionId}/control-plane/integrations/${input.kind}`, input)).data,
  saveRetention: async (institutionId: number, input: RetentionPolicy) =>
    (await api.put<RetentionPolicy>(`/institutions/${institutionId}/control-plane/retention`, input)).data,
  updatePrivacyRequest: async (institutionId: number, requestId: number, status: string, resolution_note = "") =>
    (await api.patch<PrivacyRequest>(`/institutions/${institutionId}/privacy/requests/${requestId}`, { status, resolution_note })).data,
  oneRosterExport: async (institutionId: number) =>
    (await api.get<Blob>(`/institutions/${institutionId}/integrations/oneroster/export`, { responseType: "blob" })).data,
};

