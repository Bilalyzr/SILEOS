import { api } from "./axios";

export type WhatsAppConsentState =
  | "not_started"
  | "pending"
  | "confirmed"
  | "revoked";

export interface WhatsAppConfigurationStatus {
  configured: boolean;
  api_version: string;
  phone_number_configured: boolean;
  business_account_configured: boolean;
  business_phone_configured: boolean;
  webhook_ready: boolean;
  approved_templates: string[];
  missing_fields: string[];
  missing_settings?: string[];
  display_phone_number?: string | null;
}

export interface WhatsAppAccountStatus extends WhatsAppConfigurationStatus {
  opted_in: boolean;
  contact_status: WhatsAppConsentState;
  phone: string | null;
  consent_at: string | null;
  join_url: string | null;
  join_expires_at: string | null;
}

export interface WhatsAppOptInResponse {
  status: "pending" | "confirmed";
  click_to_chat_url: string | null;
  expires_at: string | null;
  consent_at: string | null;
}

export interface WhatsAppAdminOverview extends WhatsAppConfigurationStatus {
  consent_counts: Record<WhatsAppConsentState, number> & {
    total_users: number;
  };
  eligible_by_role: Record<string, number>;
}

export interface WhatsAppAdminContact {
  user_id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  phone: string | null;
  status: WhatsAppConsentState;
  consent_at: string | null;
}

export interface WhatsAppAdminContactsPage {
  items: WhatsAppAdminContact[];
  total: number;
  offset: number;
  limit: number;
}

export interface WhatsAppCampaign {
  id: number;
  request_key: string;
  template: string;
  language: string;
  parameters: string[];
  roles: string[];
  header_image_url: string | null;
  created_at: string;
  status: string;
  recipient_count: number;
  queued: number;
  sent: number;
  delivered: number;
  read: number;
  failed: number;
  cancelled: number;
}

export interface WhatsAppCampaignCreate {
  request_key: string;
  template: string;
  language: string;
  parameters: string[];
  roles: string[];
  header_image_url?: string | null;
}

export const whatsappApi = {
  status: async () =>
    (await api.get<WhatsAppAccountStatus>("/whatsapp/status")).data,
  optIn: async (phone: string) =>
    (
      await api.post<WhatsAppOptInResponse>("/whatsapp/opt-in", {
        phone,
      })
    ).data,
  optOut: async () =>
    (
      await api.delete<{ status: "revoked" }>("/whatsapp/opt-in")
    ).data,
  adminOverview: async () =>
    (
      await api.get<WhatsAppAdminOverview>("/whatsapp/admin/overview")
    ).data,
  adminContacts: async (filters?: {
    status?: string;
    role?: string;
    search?: string;
    offset?: number;
    limit?: number;
  }) =>
    (
      await api.get<WhatsAppAdminContactsPage>("/whatsapp/admin/contacts", {
        params: filters,
      })
    ).data,
  adminCampaigns: async (limit = 100) =>
    (
      await api.get<WhatsAppCampaign[]>("/whatsapp/admin/campaigns", {
        params: { limit },
      })
    ).data,
  createAdminCampaign: async (data: WhatsAppCampaignCreate) =>
    (
      await api.post<WhatsAppCampaign>("/whatsapp/admin/campaigns", data)
    ).data,
};
