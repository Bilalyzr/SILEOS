import { api } from "@/api/axios";

export type CampusPlan = {
  key: string;
  name: string;
  description: string;
  price_label: string;
  featured: boolean;
  features: string[];
};

export type CampusLeadInput = {
  contact_name: string;
  work_email: string;
  phone: string;
  institution_name: string;
  institution_kind: "school" | "college" | "university" | "training";
  learner_count: "under-100" | "100-499" | "500-1999" | "2000-plus";
  interest: "demo" | "trial" | "quote";
  message: string;
  source: string;
  attribution: Record<string, string>;
  consent: boolean;
  website: string;
};

export const campusGrowthApi = {
  plans: async () =>
    (await api.get<{ plans: CampusPlan[] }>("/campus-growth/plans")).data.plans,
  enquire: async (input: CampusLeadInput) =>
    (
      await api.post<{ accepted: boolean; reference: string; message: string }>(
        "/campus-growth/leads",
        input,
      )
    ).data,
};

